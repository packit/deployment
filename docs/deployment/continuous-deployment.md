---
title: Continuous Deployment
---

# Continuous Deployment

## Automatic redeployment

tl;dr

> Newer images in registry are automatically imported and re-deployed.

### Details

We use [ImageStreams](https://docs.openshift.com/container-platform/latest/openshift_images/image-streams-manage.html)
as intermediary between an image registry (Quay.io) and a Deployment/StatefulSet.
It has several significant benefits:

- We can automatically trigger Deployment when a new image is pushed to the registry.
- We can roll back/revert/undo the Deployment.

`Image registry` → [^1] → `ImageStream` → `Deployment`/`StatefulSet`

[^1]:
    This is automatic (it can even take some time) on stg, but not on prod.
    On prod, where we don't want the images to
    be imported as soon as they're built, we run a
    [CronJob](https://github.com/packit/deployment/blob/main/cron-jobs/import-images/job-import-images.yaml)
    to import them (and hence re-deploy) at the day & time (currently at 2AM on Tuesday) we want.

## Manual production re-deployment

1. Trigger `:prod` images builds
   - Run [scripts/move_stable.py](https://github.com/packit/deployment/blob/main/scripts/move_stable.py) to move `stable` branches to a newer commit.

2. Import images -> re-deploy
   - If you don't want to wait for [it to be done automatically](#continuous-deployment), you can
     [do that manually](#manually-import-a-newer-image) once the images are built (check Actions in each repo).

## Manually import a newer image

tl;dr

> `DEPLOYMENT=prod make import-images`

### Details

If you need to import (and deploy) newer image(s) before the `CronJob` does
(see above), you can do that manually:

    $ oc get is
    $ oc import-image is/$NAME:prod

once a new image is pushed/built in registry. (`$NAME` is name of an image stream from `oc get is`)

There's also `import-images` target in the Makefile, so `DEPLOYMENT=prod make import-images` does this for you for all images (image streams).

To see the history of imported images in an image stream:

    $ oc describe is/$NAME:prod

## Reverting to older deployment/revision/image

`Deployment`s can be reverted with `oc rollout undo`, example:

    $ oc rollout undo deploy/packit-service [--to-revision=X]

where `X` is revision number.
See also `oc rollout history deploy/packit-service [--revision=X]`.

It's more tricky in case of `StatefulSet` which we use for workers.
`oc rollout undo` does not work with `StatefulSet` for us
(the newest image is always used, reason unknown).
So when you happen to deploy a broken worker, and you want to revert/undo it
because you don't know what's the cause/fix yet, you have to:

1.  Select older image (hash)

        $ oc describe is/packit-worker

2.  Tag the older image

        $ oc tag --source=docker quay.io/packit/packit-worker@sha256:‹older-hash› \
              packit-prod/packit-worker:‹deployment›

    And see the `packit-worker-x` pods being re-deployed from the older image.

3.  Once you've built a fixed image, run

        $ oc tag quay.io/packit/packit-worker:‹deployment› \
            packit-prod/packit-worker:‹deployment›
