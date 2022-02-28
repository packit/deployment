## PostgreSQL data migration

To write out the data from the database `pg_dumpall` command can be used (or `pg_dump packit` to dump only packit
database). The command creates a file with SQL commands for restoring the database. The only impact of running
`pg_dump`/`pg_dumpall` should be the increased I/O load and the long-running transaction it creates.
To import the data `psql` command can be used.

### Upgrade

When upgrading the database between major versions, the data can be incompatible with the new version.

We run Postgres in an Openshift pod, so the process to migrate the data can be to create a new pod (it is important to also
use a new PVC in this pod) and then dump the data from the old pod and import them to the new pod:

    $ oc exec old-postgres-pod -- pg_dumpall -U postgres > dump
    $ oc exec -it new-postgres-pod -- psql -U postgres < dump

The `postgres` service then needs to be linked to the new pod and the old pod and PVC can be deleted.
