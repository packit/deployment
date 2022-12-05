## Periodically updating ImageStreams

On prod, where we don't want the images to be imported as soon as they're built,
we run this script to import them (end hence re-deploy) into image streams
at the day & time (currently at 2AM on Tuesday) we want (via a cron job).

[Containerfile](./Containerfile) - image used by the job

[import-images.sh](./import-images.sh) - script in the image

## Deployment

The image is build via a [GitHub workflow](../../.github/workflows/build-and-push-cronjob-image.yaml)
and pushed to a [Quay.io repository](https://quay.io/repository/packit/import-images).

There is a [Helm Chart](https://github.com/packit/helm/tree/main/helm-charts/import-images)
and a [GitHub workflow](https://github.com/packit/helm/tree/main/.github/workflows/deploy-import-images.yml)
which installs/upgrades the chart to the OpenShift projects on every push.
You just have to update the [image tag](https://quay.io/repository/packit/import-images?tab=tags) in

- [packit-prod.yaml](https://github.com/packit/helm/tree/main/values/import-images/packit-prod.yaml)
- [stream-prod.yaml](https://github.com/packit/helm/tree/main/values/import-images/stream-prod.yaml)
- [fedora-source-git-prod.yaml](https://github.com/packit/helm/tree/main/values/import-images/fedora-source-git-prod.yaml)
