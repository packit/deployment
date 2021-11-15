## Periodically updating ImageStreams

OpenShift Online seems to have turned off periodical updates from image registry
to ImageStream (even we explicitly [request them](https://docs.openshift.com/container-platform/3.11/architecture/core_concepts/builds_and_image_streams.html#image-stream-mappings-working-periodic)).

As a work-around, there's a CronJob to periodically import images metadata into image streams.
See [job-import-images.yaml](./job-import-images.yaml) and `oc describe cronjob.batch/import-images`.
The job uses importimager [service account](https://docs.openshift.com/container-platform/3.11/dev_guide/service_accounts.html)
with `registry-editor` [role](https://docs.openshift.com/container-platform/3.11/admin_guide/manage_rbac.html) role added.

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
