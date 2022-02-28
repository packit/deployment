# Deploying Packit service or Stream service to Openshift

## tl;dr How to deploy

1. Obtain all the necessary [secrets](secrets/README.md).
2. Configure the deployment by creating a variable file in 'vars/' from a
   template as described in [vars/README](vars/README.md).
3. `dnf install ansible origin-clients python3-openshift`
4. `[SERVICE={service}] DEPLOYMENT={deployment} make deploy` (see
   [vars/README](vars/README.md)).

By default, the playbook checks that the local copies of the deployment and
secrets repositories are up to date, and the variable file used is up to
date with the corresponding template.

For these checks to work, you need to set `secrets_repo_url` in the variable
file used.

To disable all these check, set `check_up_to_date` to `false` in the
variable file.

To only disable comparing the variable file to the template, set
`check_vars_template_diff` to `false`.

## What's in here

- [playbooks](playbooks/) - Ansible playbooks.
- [roles](roles/) - Ansible roles.
- [vars](vars/) - Variable file(s). See [vars/README.md](vars/README.md).
- [Openshift](openshift/) - Openshift resource configuration files (templates).
- [secrets](secrets/) - secret stuff to be used from `openshift/secret-*.yml.j2`
- [scripts](scripts/) - devops scripts used in multiple repositories
- [cron-jobs](cron-jobs/) - OpenShift cron jobs
- [containers](containers/) - files used to build container images
