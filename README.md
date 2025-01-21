# Deploying Packit service or Stream service to Openshift

This repository contains Ansible playbooks/roles
to deploy our services/bots to Openshift cluster.
This file documents basic usage, for more info see
[docs](docs/) (below).

## What's in here

- [containers/](containers/) - files used to build container images
- [cron-jobs/](cron-jobs/) - OpenShift cron jobs
- [docs/](docs/) - more documentation
  - [Images](docs/deployment/images.md) - what images we have and how we build them
  - [Continuous deployment](docs/deployment/continuous-deployment.md) - how are the deployed services/bots updated
  - [Testing changes](docs/deployment/testing-changes.md) - how to test our services/bots locally
  - [Let's encrypt TLS certs](docs/deployment/tls-certs.md) - generating & renewing with `certbot`
  - [Monitoring](docs/deployment/monitoring/index.md)
  - [PostgreSQL specifics](docs/deployment/postgresql.md)
  - [Packit service deployment specifics](docs/deployment/specifics/packit-service.md)
  - [Fedora source-git bot deployment specifics](docs/deployment/specifics/fedora-source-git.md)
  - [CentOS Stream source-git bot deployment specifics](docs/deployment/specifics/centos-stream-source-git.md)
  - [Logs](docs/deployment/monitoring/logs.md) - how we aggregate worker logs and where to find them
- [playbooks/](playbooks/) - Ansible playbooks
- [roles/](roles/) - Ansible roles
- [vars/](vars/) - Variable file(s). See [vars/README.md](vars/README.md).
- [openshift/](openshift/) - Openshift resource configuration files (templates).
- [secrets/](secrets/) - secret stuff to be used from `openshift/secret-*.yml.j2`
- [scripts/](scripts/) - devops scripts used in multiple repositories

## tl;dr How to deploy

1. Configure the deployment by creating a variable file in 'vars/' from a
   template as described in [vars/README](vars/README.md).
2. Install some dependencies:
   - `dnf install ansible python3-openshift python3-passlib jq make`
   - `dnf install origin-clients` or (for a more recent version) download
     `openshift-client-linux` from the [OKD
     releases](https://github.com/openshift/okd/releases) page, unpack it, and
     place `oc` in your `$PATH` (ex: `~/.local/bin`).
   - Download the [Bitwarden
     CLI](https://bitwarden.com/help/cli/#download-and-install),
     unpack and place it in your `$PATH` (ex: `~/.local/bin`).
3. `[SERVICE={service}] DEPLOYMENT={deployment} make deploy` (see
   [vars/README](vars/README.md)).

By default, the playbook checks that the local copy of the deployment is
up-to-date, and the variable file used is
up-to-date with the corresponding template.

To disable these checks, set `check_up_to_date` to `false` in the
variable file.

To only disable comparing the variable file to the template, set
`check_vars_template_diff` to `false`.

### Partial deployments

To run only the tasks related to some of the services, this way doing a
partial deployment, you can set the `TAGS` environment variable before calling
`make`. For example, to run only the tasks to deploy Redict and Redis
Commander, run:

    $ DEPLOYMENT=dev TAGS="redict,redis-commander" make deploy

Use `make tags` to list the currently available tags.

## See [docs/](docs/) for more documentation.
