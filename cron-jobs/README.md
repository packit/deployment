# Opneshift cron jobs

Currently cron jobs configuration is not fully consistent, there is issue opened for it (#112).

## rebuild-base-image

The `rebuild-base-image` CronJob is rebuilding the base image using a DockerHub webhook. The webhook is stored in the secrets repo.

Rebuild-base-image is deployed using root Makefile:

```shell script
DEPLOYMENT=stg make deploy-rebuild-base-image
```

Note:
This cron job is not related to specific deployment stage and because there is no dedicated
namespace in OpenShift for this purpose, it is deployed to packit-stg namespace.
