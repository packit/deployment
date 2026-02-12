---
title: Celery task queues
---

# Celery task queues

This document covers inspecting and managing Celery task queues in the deployed
Packit service.

## Queue overview

The service uses three Celery queues:

- `short-running` - default queue for quick tasks
- `long-running` - for operations requiring running local commands/sandcastle use (builds, sync-release)
- `rate-limited` - for tasks re-queued due to API rate limits

Tasks are stored in Valkey (Redis-compatible) database. All tasks use
[`acks_late=True`](https://docs.celeryq.dev/en/stable/userguide/tasks.html#Task.acks_late),
meaning tasks are acknowledged after completion. This means in-flight tasks
have their messages tracked in Valkey until the worker finishes processing them.

## Inspecting queue size and content

### Using Flower (Web UI)

Flower is deployed for monitoring Celery workers and tasks. It's exposed as a
Service (not a Route), so you need to port-forward to access it:

```
$ oc port-forward svc/flower 5555:5555
```

Then open http://localhost:5555 in your browser.

Flower shows:

- Active, processed, and failed tasks
- Worker status and statistics
- Task details and results

See [Flower documentation](https://flower.readthedocs.io/en/latest/) for more
details.

### Using Celery inspect commands

You can also use Celery's built-in inspection to see active/scheduled tasks:

```
$ oc exec packit-worker-short-running-0 -- celery -A packit_service.worker.tasks inspect active
$ oc exec packit-worker-short-running-0 -- celery -A packit_service.worker.tasks inspect reserved
$ oc exec packit-worker-short-running-0 -- celery -A packit_service.worker.tasks inspect scheduled
```

See [Celery Workers Guide - Inspecting workers](https://docs.celeryq.dev/en/stable/userguide/workers.html#inspecting-workers)
for more inspection commands.

## Purging the task queue

After a long outage, the task queue may accumulate too many stale tasks that no
longer make sense to process. This section describes how to safely purge the
queue.

**Important:** Purging while workers are actively processing tasks can cause
issues - workers may fail to acknowledge completed tasks, potentially leading
to duplicate processing on restart.

### Safe purge

1. **Optionally scale down workers** to reduce the number of prefetched tasks:

   ```
   $ oc scale statefulset/packit-worker-short-running --replicas=0
   $ oc scale statefulset/packit-worker-long-running --replicas=1
   ```

2. **Purge the queues** using Celery's built-in
   [`purge`](https://docs.celeryq.dev/en/stable/reference/cli.html#celery-purge)
   command. This can be run from any worker pod and will purge all queues:

   ```
   $ oc exec packit-worker-long-running-0 -- celery -A packit_service.worker.tasks purge -Q short-running,long-running,rate-limited
   ```

   Using `-f` flag skips the confirmation prompt. With `-Q` you can also specify only subset of queues.

3. **Scale workers back up** (if scaled down):

   ```
   $ oc scale statefulset/packit-worker-short-running --replicas=<N>
   $ oc scale statefulset/packit-worker-long-running --replicas=<N>
   ```
