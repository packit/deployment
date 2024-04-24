---
title: Redict
---

## Seamless migration between providers

We have tested a seamless migration from Redis to Redict on our production
deployment. To reproduce:

1. We have deployed Redict to our production cluster.
2. Using remote shell and `redict-cli` run:

   ```sh
   replicaof redis 6379
   ```

   This converts the Redict instance into a read-only replica of the Redis.

3. After the data exchange is done, change **all** references in variables to
   redis to point to the new hostname, in this case `redis → redict`.
4. Simultaneously run the deployment with the changed hostnames and via
   `redict-cli` run:

   ```sh
   replicaof no one
   ```

   to make the redict deployment the primary one.

5. (optional) For safety reasons and easier rollback, it's possible to convert
   the former Redis deployment into a replica of Redict, just in case it needs
   to be reverted without loss of data. For this you can run in `redis-cli`:

   ```sh
   replicaof redict 6379
   ```

:::warning References to Redis

Redis is being referenced from:

- `packit-service` (API endpoint)
- `packit-service-fedmsg` (Fedora Messaging listener)
- `packit-service-beat` (triggers periodic tasks)
- `packit-worker` (runs the jobs provided by API, Fedora Messaging and “beat”)
- `flower` (monitoring of the Celery queues)

:::
