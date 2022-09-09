## Periodically updating ImageStreams

On prod, where we don't want the images to be imported as soon as they're built,
we run this cron job to import them (end hence re-deploy) into image streams
at the day & time (currently at 2AM on Tuesday) we want.

See [job-import-images.yaml](./job-import-images.yaml) and `oc describe cronjob.batch/import-images`.
The job uses importimager service account with `registry-editor`
[role](https://docs.openshift.com/container-platform/4.11/authentication/using-rbac.html) added.

If you ever needed to re-create it, just do:

```bash
$ oc create serviceaccount importimager
$ oc policy add-role-to-user registry-editor -z importimager
```

[Containerfile](./Containerfile) - image used by the job

[import-images.sh](./import-images.sh) - script in the image

## How to deploy the cron job

Edit [job-import-images.yaml](./job-import-images.yaml) if needed
(to change `HOST`, `TOKEN`, `SERVICE` or `DEPLOYMENT`) and run `make deploy`.
