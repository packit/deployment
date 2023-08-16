---
title: PostgreSQL
---

# Logs

See `/var/lib/pgsql/data/userdata/log/postgresql-*.log` in the pod's Terminal.

# Data

## What's inside, ER Diagram, backups

See https://github.com/packit/packit-service/tree/main/docs/database

## Move data to another instance

To write out the data from the database `pg_dump packit` can be used.
The command creates a file with SQL commands for restoring the database.
To import the data `psql` command can be used.

## Upgrade

When upgrading the database between major versions, the data can be incompatible with the new version.

We run Postgres in an Openshift pod, so the process to migrate the data can be to create a new pod (it is important to also
use a new PVC in this pod) and then dump the data from the old pod and import them to the new pod:

    $ oc exec old-postgres-pod -- pg_dumpall -U postgres > dump
    $ oc exec -it new-postgres-pod -- psql -U postgres < dump

Or see instructions in https://github.com/packit/packit-service/tree/main/docs/database#using-live-data-locally

The `postgres` service then needs to be linked to the new pod and the old pod and PVC can be deleted.
