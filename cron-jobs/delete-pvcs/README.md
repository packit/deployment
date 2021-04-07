## Periodically deleting old Persistent Volume Claims (PVCs)

[It happens from time to time](https://github.com/packit/packit-service/issues/409) that leftover PVCs in a sandbox namespace consume all storage quota.

As a work-around, here's a CronJob to periodically delete old PVCs.
See CronJob definition [job-delete-pvcs.yaml](./job-delete-pvcs.yaml) or `oc describe cronjob/delete-pvcs`.
It runs this script: [delete-pvcs.sh](./delete-pvcs.sh)

The job uses
[pvcdeleter@stg](https://admin-console.pro-eu-west-1.openshift.com/k8s/ns/packit-stg-sandbox/serviceaccounts/pvcdeleter) or
[pvcdeleter@prod](https://admin-console.pro-eu-west-1.openshift.com/k8s/ns/packit-prod-sandbox/serviceaccounts/pvcdeleter)
[service account](https://docs.openshift.com/container-platform/3.11/dev_guide/service_accounts.html)
with `edit` [role](https://docs.openshift.com/container-platform/3.11/admin_guide/manage_rbac.html) added.

If you ever needed to re-create it, just do:

```bash
$ oc create serviceaccount pvcdeleter
$ oc policy add-role-to-user edit -z pvcdeleter
```

`edit` role is quite powerful, but the following role just for listing/deleting PVCs doesn't seem to work:

```bash
$ oc create role pvcdelete --verb=delete,list --resource=persistentvolumeclaims
$ oc policy add-role-to-user pvcdelete -z pvcdeleter
```

## How to deploy the cron job

Edit [job-delete-pvcs.yaml](./job-delete-pvcs.yaml) if needed
(to change `HOST`, `TOKEN` or `DEPLOYMENT`) and run `make deploy`.
