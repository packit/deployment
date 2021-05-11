# Ansible playbooks and scripts for deploying packit-service to Openshift

## tl;dr How to deploy

1. Obtain all the necessary [secrets](/secrets/README.md).
2. in [vars](vars/) copy `{deployment}_template.yml` to `{deployment}.yml` where `{deployment}` is one of `prod`, `stg` or `dev` and fill in values
3. `dnf install ansible origin-clients python3-openshift`
4. `DEPLOYMENT={deployment} make deploy`

## What's in here

- [playbooks](playbooks/) - Ansible playbooks.
- [roles](roles/) - Ansible roles.
- [vars](vars/) - Variable file(s). See [vars/README.md](vars/README.md).
- [Openshift](openshift/) - Openshift resource configuration files (templates).
- [secrets](secrets/) - secret stuff to be used from `openshift/secret-*.yml.j2`
- [scripts](scripts/) - devops scripts used in multiple repositories
- [cron-jobs](cron-jobs/) - OpenShift cron jobs
- [containers](containers/) - files used to build container images

### Images

We build separate images for

- [service / web server](https://quay.io/repository/packit/packit-service) - accepts webhooks and tasks workers
- [workers](https://quay.io/repository/packit/packit-worker) - do the actual work
- [fedora messaging consumer](https://quay.io/repository/packit/packit-service-fedmsg) - listens on fedora messaging for events from Copr and tasks workers
- [CentOS messaging consumer](https://quay.io/repository/packit/packit-service-centosmsg) - listens on the CentOS MQTT message bus for events from git.centos.org
- [Sandcastle](https://quay.io/repository/packit/sandcastle) - sandboxing

#### Production vs. Staging images

Separate images are built for staging and production deployment.
Staging images are `:stg` tagged and built from `main` of `packit-service`, `packit-service-fedmsg`, `packit-service-centosmg`, `sandcastle` and `dashboard`.
Production images are `:prod` tagged and built from `stable` branch of `packit-service`, `packit-service-fedmsg`, `packit-service-centosmg`, `sandcastle` and `dashboard`.
To move `stable` branch to a newer 'stable' commit:

- git branch -f stable commit-hash
- git push [-u upstream] stable

#### Image build process

Images are automatically built and pushed to [Quay.io](https://quay.io/organization/packit)
by a Github workflow whenever a new commit is pushed to `main` or `stable` branch.

In each repo (which builds images) see

- `Actions` tab
- .github/workflows/\*.yml for configuration of the Action/workflow

For more details about local builds see [packit-service/CONTRIBUTING.md](https://github.com/packit/packit-service/blob/main/CONTRIBUTING.md#building-images-locally)

### Continuous Deployment

tl;dr: Newer images in registry are automatically imported and re-deployed.

Long story:
We use [ImageStreams](https://docs.openshift.com/container-platform/3.11/architecture/core_concepts/builds_and_image_streams.html#image-streams)
as intermediary between an image registry (Quay.io) and a Deployment/StatefulSet.
It has several significant benefits:

- We can automatically trigger Deployment when a new image is pushed to the registry.
- We can rollback/revert/undo the Deployment (previously we had to use image digests to achieve this).

`Image registry` -> [1] -> `ImageStream` -> [2] -> `DeploymentConfig`/`StatefulSet`

[1] set to automatic ([here](https://github.com/packit-service/deployment/blob/main/openshift/imagestream.yml.j2#L36)), however OpenShift Online has this turned off.
We run a [CronJob](https://github.com/packit-service/deployment/blob/main/cron-jobs/job-import-images.yaml) to work-around this.
More info [here](./cron-jobs/README.md).
It runs (i.e. imports newer images and re-deploys them)

- STG: Once every hour (at minute 0)
- PROD: At 2AM on Monday

[2] automatic, [example](https://github.com/packit-service/deployment/blob/main/openshift/deployment.yml.j2#L98)

### Manually import a newer image

tl;dr; `DEPLOYMENT=prod make import-images`

Long story:
If you need to import (and deploy) newer image(s) before the CronJob does
(see above), you can [do that manually](https://docs.openshift.com/container-platform/3.11/dev_guide/managing_images.html#importing-tag-and-image-metadata):

    $ oc import-image is/packit-{service|service-fedmsg|worker|dashboard|service-centosmsg}:<deployment>

once a new image is pushed/built in registry.

There's also 'import-images' target in the Makefile, so `DEPLOYMENT=prod make import-images` does this for you for all images (image streams).

### Partial deployments

To run only the tasks related to some of the services, this way doing a
partial deployment, you can set the `TAGS` environment variable before calling
`make`. For example, to run only the tasks to deploy Redis and Redis
Commander, run:

    $ DEPLOYMENT=dev TAGS="redis,redis-commander" make deploy

Use `make tags` to list the currently available tags.

### Reverting to older deployment/revision/image

`DeploymentConfig`s (i.e. service & service-fedmsg) can be reverted with `oc rollout undo`:

    $ oc rollout undo dc/packit-service [--to-revision=X]
    $ oc rollout undo dc/packit-service-fedmsg [--to-revision=X]

where `X` is revision number.
See also `oc rollout history dc/packit-service [--revision=X]`.

It's more tricky in case of `StatefulSet` which we use for worker.
`oc rollout undo` does not seem to work with `StatefulSet`
(even it [should](https://github.com/kubernetes/kubernetes/pull/49674)).
So when you happen to deploy broken worker and you want to revert/undo it
because you don't know what's the cause/fix yet, you have to:

1. `oc describe is/packit-worker` - select older image
2. `oc tag --source=docker usercont/packit-worker@sha256:<older-hash> myproject/packit-worker:<deployment>`
   And see the `packit-worker-x` pods being re-deployed from the older image.

### Prod re-deployment

1. Trigger `:prod` images builds

- Run [scripts/move_stable.py](scripts/move_stable.py) to move `stable` branches to a newer commit.

2. Import images -> re-deploy

- If you don't want to wait for [it to be done automatically](#continuous-deployment) you can
  [do that manually](#manually-import-a-newer-image) once the images are built (check Actions in each repo).

### How do I test my changes?

#### docker-compose (quick & dirty)

There's a [docker-compose.yml in packit-service](https://github.com/packit-service/packit-service/blob/main/docker-compose.yml).
See [Running packit-service locally](https://github.com/packit-service/packit-service/blob/main/CONTRIBUTING.md#running-packit-service-locally) for how to make that work.

#### oc cluster up (slow & better)

Because we run the service in OpenShift the more reliable way to test it
is to run an Openshift cluster locally and deploy the service there.
`oc cluster up` spawns the Openshift cluster.
Create `secrets/dev/` (steal them from our secret repo).
`cd vars; cp dev_template.yml dev.yml` and in `dev.yml` set `api_key` to the output of `oc whoami -t`.

Run `DEPLOYMENT=dev make deploy`.
That will also push locally built images (`:dev`) into the cluster's registry
(make sure you have `push_dev_images: true` in `vars/dev.yml`).

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

## Obtaining a Let's Encrypt cert using `certbot`

Please bear in mind this is the easiest process I was able to figure out: there
is a ton of places for improvements and ideally make it automated 100%.

We are using multi-domain wildcard certificates for following domains:

- \*.packit.dev
- \*.prod.packit.dev
- \*.stg.packit.dev

In case the procedure bellow does not work,
[previously used http challenge](https://github.com/packit-service/deployment/blob/008f5eaad69a620c54784f1fc19c7c775af9ec7d/README.md#obtaining-a-lets-encrypt-cert-using-certbot)
can be used instead.
Be aware that the http challenge approach is more complex, includes destructive actions and longer downtime.

TL;DR

1. Check prerequisites.
2. Run certbot to obtain the challenges.
3. Configure DNS TXT records based on values requested in 2.
4. Update secrets repository.
5. Re-deploy stg&prod.

_Note: If certbot is executed against multiple domains, step 3. is repeated for each domain._

### 1. Prerequisites

Make sure the DNS is all set up:

    $ dig prod.packit.dev
    ; <<>> DiG 9.11.28-RedHat-9.11.28-1.fc33 <<>> prod.packit.dev
    ;; QUESTION SECTION:
    ;prod.packit.dev.		IN	A
    ;; ANSWER SECTION:
    prod.packit.dev.	282	IN	CNAME	elb.e4ff.pro-eu-west-1.openshiftapps.com.
    elb.e4ff.pro-eu-west-1.openshiftapps.com. 3599 IN CNAME	pro-eu-west-1-infra-1781350677.eu-west-1.elb.amazonaws.com.
    pro-eu-west-1-infra-1781350677.eu-west-1.elb.amazonaws.com. 59 IN A 52.208.12.108
    pro-eu-west-1-infra-1781350677.eu-west-1.elb.amazonaws.com. 59 IN A 52.209.166.166

Check if you have access to packit.dev domain in
[Google Domains](https://domains.google.com/m/registrar/packit.dev).

Check/install certbot locally. You can either follow
[instructions for Apache on Fedora](https://certbot.eff.org/lets-encrypt/fedora-apache.html)
or simply `dnf install certbot` on your machine (the instructions tell you to do that on server).

### 2. Run certbot to obtain the challenges.

Run certbot:

    $ certbot certonly --config-dir ~/.certbot --work-dir ~/.certbot --logs-dir ~/.certbot --manual --preferred-challenges dns --email user-cont-team@redhat.com -d *.packit.dev -d *.prod.packit.dev -d *.stg.packit.dev

You will be asked to set TXT record for every domain requested:

    - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    Please deploy a DNS TXT record under the name
    _acme-challenge.packit.dev with the following value:

    123456abcdef

    Before continuing, verify the record is deployed.
    - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    Press Enter to Continue

### 3. Update DNS record

Go to [Google Domains](https://domains.google.com/m/registrar/packit.dev/dns)
and create/set the corresponding value:
TXT record called `_acme-challenge`
(or `_acme-challenge.prod` or `acme-challenge.stg` per instructions).
If those records already exist (from previous run), don't create new records,
just edit current ones (or first delete the old ones and then create new ones).

Wait till it's distributed - in another terminal watch nslookup
and once it returns the configured value

    [~/]$ watch -d nslookup -q=TXT _acme-challenge.packit.dev
    Server:         127.0.0.53
    Address:        127.0.0.53#53

    Non-authoritative answer:
    _acme-challenge.packit.dev      text = "123456abcdef"

    Authoritative answers can be found from:

    Ctrl+c

Go to the terminal with certbot command waiting for your action and hit Enter.

Repeat this for all requested domains.

### 4. Update secrets repository

Copy certificates to secrets repository (prod & stg)

    cp ~/.certbot/live/packit.dev/{fullchain,privkey}.pem <cloned secrets repo>/secrets/prod/
    cp ~/.certbot/live/packit.dev/{fullchain,privkey}.pem <cloned secrets repo>/secrets/stg/

Push, create merge request and merge.

### 5.Re-deploy stg and prod environment:

    DEPLOYMENT=stg make deploy
    DEPLOYMENT=prod make deploy

Docs: https://certbot.eff.org/docs/using.html#manual

### How to test the TLS deployment

If you want to inspect local certificates, you can use `certtool` (`gnutls-utils` package)
to view the cert's metadata:

    X.509 Certificate Information:
        Version: 3
        Serial Number (hex): 04f4864b597f9c0859260d88e04cfabfeeac
        Issuer: CN=R3,O=Let's Encrypt,C=US
        Validity:
            Not Before: Wed Feb 17 14:46:25 UTC 2021
            Not After: Tue May 18 14:46:25 UTC 2021

## Monitoring of packit-service

### Pushgateway

To record metrics from Celery tasks we are going to use [Prometheus Pushgateway](https://github.com/prometheus/pushgateway) which is [deployed](./openshift/pushgateway.yml.j2) in our cluster.
It can collect the metrics from the workers and provide the `/metrics` endpoint for Prometheus.
There is a Prometheus instance running in OpenShift PSI, which is going to scrape the `/metrics` endpoint and then it will be possible
to visualize them. Therefore the `/metrics` endpoint needs to be publicly
accessible - it is exposed on https://workers.packit.dev/metrics for metrics of the production instance and https://workers.stg.packit.dev/metrics
for metrics of the staging instance.
We use nginx ([definition](./openshift/nginx.yml.j2)) to serve as a reverse proxy for the pushgateway, which enables us to allow only
`GET` requests and forward these to pushgateway (workers can send `POST` requests internally).
