---
title: Testing Changes
---

# How do I test my changes?

In all cases, you first need to [get or generate expected secrets in `secrets/{SERVICE}/dev/`](secrets#running-a-servicebot-locally).

## `docker-compose` (quick & dirty)

Before you follow [Running packit-service locally](https://github.com/packit/packit-service/blob/main/CONTRIBUTING.md#running-packit-service-locally):

- [get/generate the secrets](secrets#running-a-servicebot-locally)
- run `DEPLOYMENT=dev make render-secrets-from-templates` to create `packit-service.yaml` and `fedora.toml` from their templates and `extra-vars.yml`
- copy the `secrets/{SERVICE}/dev/*` to `secrets/{SERVICE}/dev/` in cloned `packit-service` repo

## `oc cluster up` (slow & better)

Because we run the service in OpenShift the more reliable way to test it
is to run an Openshift cluster locally and deploy the service there.
`oc cluster up` spawns the Openshift (v3) cluster.
[Create `secrets/packit/dev/`](secrets#running-a-servicebot-locally),
`cd vars/packit; cp dev_template.yml dev.yml` and
in `dev.yml` set `api_key` to the output of `oc whoami -t`.

Run `DEPLOYMENT=dev make deploy`.
That will also push locally built images (`:dev`) into the cluster's registry
(make sure you have `push_dev_images: true` in `vars/packit/dev.yml`).

## MiniShift

Similar to above 'oc cluster up' you can run [minishift](https://www.okd.io/minishift/) to get
a local OpenShift cluster.
In addition to the above, you need to use `docker` and `oc`
from the minishift environment after you start minishift:

    $ eval $(minishift docker-env)
    $ eval $(minishift oc-env)
    $ oc config use-context minishift

and then build worker & service images (`make worker; make service` in `packit-service` repo)
with Docker, before you run `DEPLOYMENT=dev make deploy`.

## Staging (quick & reliable, but don't break it)

If you're fairly sure your changes won't do any harm,
you can temporarily get hold of staging instance for that.

For example, in case of `packit-worker`:

- in cloned [packit-service repo](https://github.com/packit/packit-service):
  - `make worker`
  - `podman tag quay.io/packit/packit-worker:dev quay.io/packit/packit-worker:stg`
  - `podman push quay.io/packit/packit-worker:stg`
- in deployment: `DEPLOYMENT=stg make import-images`

Once you're done you should [revert to older image](continuous-deployment#reverting-to-older-deploymentrevisionimage).
Or it will be automatically replaced once a packit-service PR is merged.

## Zuul

We have to encrypt the secrets, because we are using them in Zuul CI.
This repository provides helpful playbook to do this with one command:

    DEPLOYMENT=stg make zuul-secrets

### How are the secrets encrypted?

Zuul provides a public key for every project. The ansible playbook downloads Zuul repository and pass the project tenant and name as parameters to encryption script. This script then encrypts files with public key of the project.
For more information please refer to [official docs](https://ansible.softwarefactory-project.io/docs/user/zuul_user.html#create-a-secret-to-be-used-in-jobs).

### Test Deployment locally with OpenShift Local

For using OpenShift Local you need a _pull secret_, download it here: https://console.redhat.com/openshift/create/local. Save it in a file called `secrets\openshift-local-pull-secret.yml` following this format:

```
---
pull_secret: <<< DOWNLOADED PULL SECRET CONTENT >>>
```

Populate the `secrets` dir with all the other secrets.
You _should use_ your own secrets but if you have access to `stg` secrets
you can also do:

```
DEPLOYMENT=stg make download-secrets
```

Now you can create and start the OpenShift Local cluster (it take as long as an hour) in a Vagrant Virtual Machine with:

```
make oc-cluster-create
```

And once it is up and running you can test the `packit-service` deployment with the command:

```
make tmt-tests
```

This command will sshed the virtual machine and run the tests there (`make test-deploy`),
you can run the tests as many time you want as long as the virtual machine is up and running and the `crc cluster` is started (`make oc-cluster-up` after every `make oc-cluster-down`).
You can skip the `tmt` environment and run the test directly inside the VM using `make oc-cluster-ssh` and `cd /vagrant && make test-deploy`.

You can destroy the `libvirt` machine with `make oc-cluster-destroy` and re-create it again with `make oc-cluster-create`.
