## Work-around for Openshift Online not periodically updating ImageStreams

OpenShift Online (where we currently run Packit Service) seems to have
turned off periodical updates from image registry to ImageStream
(even we explicitly [request them](https://docs.openshift.com/container-platform/3.11/architecture/core_concepts/builds_and_image_streams.html#image-stream-mappings-working-periodic)).

[job-import-images.yml](./job-import-images.yml) - CronJob to periodically import images metadata into image streams. We use this on `stg`, see `oc describe cronjob.batch/import-images`.
There's [imageimporter](https://admin-console.pro-eu-west-1.openshift.com/k8s/ns/packit-stg/serviceaccounts/importimager) [service account](https://docs.openshift.com/container-platform/3.11/dev_guide/service_accounts.html) with `registry-editor` [role](https://docs.openshift.com/container-platform/3.11/admin_guide/manage_rbac.html) role added.

[Dockerfile](./Dockerfile) - image used by the job

[import-images.sh](./import-images.sh) - script in the image


## Obtaining a Let's Encrypt cert using `certbot`

* serve-acme-challenge.py - see [main README](../README.md#just-do-it)
