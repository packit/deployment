### How do I test my changes?

#### docker-compose (quick & dirty)

There's a [docker-compose.yml in packit-service](https://github.com/packit/packit-service/blob/main/docker-compose.yml).
See [Running packit-service locally](https://github.com/packit/packit-service/blob/main/CONTRIBUTING.md#running-packit-service-locally) for how to make that work.

#### oc cluster up (slow & better)

Because we run the service in OpenShift the more reliable way to test it
is to run an Openshift cluster locally and deploy the service there.
`oc cluster up` spawns the Openshift cluster.
Create `secrets/packit/dev/` (steal them from our secret repo).
`cd vars/packit; cp dev_template.yml dev.yml` and
in `dev.yml` set `api_key` to the output of `oc whoami -t`.

Run `DEPLOYMENT=dev make deploy`.
That will also push locally built images (`:dev`) into the cluster's registry
(make sure you have `push_dev_images: true` in `vars/packit/dev.yml`).

#### minishift

Similar to above 'oc cluster up' you can run [minishift](https://www.okd.io/minishift/) to get
a local OpenShift cluster.
In addition to the above, you need to use `docker` and `oc`
from the minishift environment after you start minishift:

    $ eval $(minishift docker-env)
    $ eval $(minishift oc-env)
    $ oc config use-context minishift

and then build worker & service images (`make worker; make service` in `packit-service` repo)
with Docker, before you run `DEPLOYMENT=dev make deploy`.

#### Staging (quick & reliable & but don't break it)

If you're lazy and you're sure your changes won't do any harm, you can temporarily get hold of staging instance for that.
Just build & push `packit-worker` and you can play.

- in packit-service repo:
  - `make worker`
  - `podman tag quay.io/packit/packit-worker:dev quay.io/packit/packit-worker:stg`
  - `podman push quay.io/packit/packit-worker:stg`
- in deployment: `DEPLOYMENT=stg make import-images`

Once you're done you should [revert to older image](#reverting-to-older-deploymentrevisionimage).
Or it will be automatically replaced once a packit-service PR is merged.

### Generating secrets for local packit-service deployment

Local deployment of Packit service needs some secrets which can be generated using the steps listed below:

1. Create `dev` directory under `secrets`
2. Create a [new GitHub app](https://github.com/settings/apps/new) or [open existing one](https://github.com/settings/apps) and download key file as `secrets/dev/private-key.pem`
3. Replace variables with your user specific values in `roles/generate-secrets/vars/main.yml`
4. Run the playbook `make generate-local-secrets`

Then, copy the `secrets` directory to your `packit-service` directory

## Zuul

We have to encrypt the secrets, because we are using them in Zuul CI.
This repository provides helpful playbook to do this with one command:

    DEPLOYMENT=stg make zuul-secrets

### How are the secrets encrypted?

Zuul provides a public key for every project. The ansible playbook downloads Zuul repository and pass the project tenant and name as parameters to encryption script. This script then encrypts files with public key of the project.
For more information please refer to [official docs](https://ansible.softwarefactory-project.io/docs/user/zuul_user.html#create-a-secret-to-be-used-in-jobs).
