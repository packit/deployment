### Continuous Deployment

tl;dr: Newer images in registry are automatically imported and re-deployed.

Long story:
We use [ImageStreams](https://docs.openshift.com/container-platform/3.11/architecture/core_concepts/builds_and_image_streams.html#image-streams)
as intermediary between an image registry (Quay.io) and a Deployment/StatefulSet.
It has several significant benefits:

- We can automatically trigger Deployment when a new image is pushed to the registry.
- We can rollback/revert/undo the Deployment.

`Image registry` -> [1] -> `ImageStream` -> `DeploymentConfig`/`StatefulSet`

[1] This is automatic on stg, but not on prod. On prod, where we don't want the images to
be imported as soon as they're built, we run a
[CronJob](https://github.com/packit/deployment/blob/main/cron-jobs/import-images/job-import-images.yaml)
to import them (end hence re-deploy) at the day & time (currently at 2AM on Tuesday) we want.

### Manually import a newer image

tl;dr; `DEPLOYMENT=prod make import-images`

Long story:
If you need to import (and deploy) newer image(s) before the CronJob does
(see above), you can [do that manually](https://docs.openshift.com/container-platform/3.11/dev_guide/managing_images.html#importing-tag-and-image-metadata):

    $ oc import-image is/packit-{service|worker|dashboard|service-fedmsg}:<deployment>

once a new image is pushed/built in registry.

There's also 'import-images' target in the Makefile, so `DEPLOYMENT=prod make import-images` does this for you for all images (image streams).

### Partial deployments

To run only the tasks related to some of the services, this way doing a
partial deployment, you can set the `TAGS` environment variable before calling
`make`. For example, to run only the tasks to deploy Redis and Redis
Commander, run:

    $ DEPLOYMENT=dev TAGS="redis,redis-commander" make deploy

Use `make tags` to list the currently available tags.

### Reverting to older deployment/revision/image

`DeploymentConfig`s (i.e. service & service-fedmsg) can be reverted with `oc rollout undo`:

    $ oc rollout undo dc/packit-service [--to-revision=X]
    $ oc rollout undo dc/packit-service-fedmsg [--to-revision=X]

where `X` is revision number.
See also `oc rollout history dc/packit-service [--revision=X]`.

It's more tricky in case of `StatefulSet` which we use for worker.
`oc rollout undo` does not seem to work with `StatefulSet`
(even it [should](https://github.com/kubernetes/kubernetes/pull/49674)).
So when you happen to deploy broken worker and you want to revert/undo it
because you don't know what's the cause/fix yet, you have to:

1. `oc describe is/packit-worker` - select older image
2. `oc tag --source=docker usercont/packit-worker@sha256:<older-hash> myproject/packit-worker:<deployment>`
   And see the `packit-worker-x` pods being re-deployed from the older image.

### Prod re-deployment

1. Trigger `:prod` images builds

- Run [scripts/move_stable.py](scripts/move_stable.py) to move `stable` branches to a newer commit.

2. Import images -> re-deploy

- If you don't want to wait for [it to be done automatically](#continuous-deployment) you can
  [do that manually](#manually-import-a-newer-image) once the images are built (check Actions in each repo).
