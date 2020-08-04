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

- [service / web server](https://hub.docker.com/r/usercont/packit-service) - accepts webhooks and tasks workers
- [fedora messaging consumer](https://hub.docker.com/r/usercont/packit-service-fedmsg) - listens on fedora messaging for events from Copr and tasks workers
- [CentOS messaging consumer](https://hub.docker.com/r/usercont/packit-service-centosmsg) - listens on the CentOS MQTT message bus for events from git.centos.org
- [workers](https://hub.docker.com/r/usercont/packit-service-worker) - do the actual work

#### Production vs. Staging images

Separate images are built for staging and production deployment.
Staging images are `:stg` tagged and built from `master` of `packit`, `packit-service`, `packit-service-fedmsg`, `packit-service-centosmg` and `sandcastle`.
Production images are `:prod` tagged and built from `stable` branch of `packit`, `packit-service`, `packit-service-fedmsg`, `packit-service-centosmg` and `sandcastle. To move`stable` branch to a newer 'stable' commit:

- git branch -f stable commit-hash
- git push [-u upstream] stable

#### Image build process

Image builds are triggered by new commits on Docker Hub. ([Autobuild docs](https://docs.docker.com/docker-hub/builds/))

In packit-service we use a custom build hook to be able to inject ENV variables
provided by the build process. ([docs](https://docs.docker.com/docker-hub/builds/advanced/))

From more details about local builds pls check [link](https://github.com/packit/packit-service/blob/master/CONTRIBUTING.md#building-images-locally)

### Continuous Deployment

tl;dr: Newer images in registry are automatically imported and re-deployed.

Long story:
We use [ImageStreams](https://docs.openshift.com/container-platform/3.11/architecture/core_concepts/builds_and_image_streams.html#image-streams) as intermediary between an image registry (Docker Hub) and a Deployment/StatefulSet. It has several significant benefits:

- We can automatically trigger Deployment when a new image is pushed to the registry.
- We can rollback/revert/undo the Deployment (previously we had to use image digests to achieve this).

`Image registry` -> [1] -> `ImageStream` -> [2] -> `DeploymentConfig`/`StatefulSet`

[1] set to automatic ([here](https://github.com/packit-service/deployment/blob/master/openshift/imagestream.yml.j2#L36)), however OpenShift Online has this turned off.
We run a [CronJob](https://github.com/packit-service/deployment/blob/master/cron-jobs/job-import-images.yaml) to work-around this.
More info [here](./cron-jobs/README.md).
It runs (i.e. imports newer images and re-deploys them)

- STG: Once every hour (at minute 0)
- PROD: At 2AM on Monday

[2] automatic, [example](https://github.com/packit-service/deployment/blob/master/openshift/deployment.yml.j2#L98)

### Manually import a newer image

tl;dr; `DEPLOYMENT=prod make import-images`

Long story:
If you need to import (and deploy) newer image(s) before the CronJob does
(see above), you can [do that manually](https://docs.openshift.com/container-platform/3.11/dev_guide/managing_images.html#importing-tag-and-image-metadata):

```
$ oc import-image is/packit-{service|service-fedmsg|worker|dashboard|service-centosmsg}:<deployment>
```

once a new image is pushed/built in registry.

There's also 'import-images' target in the Makefile, so `DEPLOYMENT=prod make import-images` does this for you for all images (image streams).

### Partial deployments

To run only the tasks related to some of the services, this way doing a
partial deployment, you can set the `TAGS` environment variable before calling
`make`. For example, to run only the tasks to deploy Redis and Redis
Commander, run:

```
$ DEPLOYMENT=dev TAGS="redis,redis-commander" make deploy
```

Use `make tags` to list the currently available tags.

### Reverting to older deployment/revision/image

`DeploymentConfig`s (i.e. service & service-fedmsg) can be reverted with `oc rollout undo`:

```
$ oc rollout undo dc/packit-service [--to-revision=X]
$ oc rollout undo dc/packit-service-fedmsg [--to-revision=X]
```

where `X` is revision number.
See also `oc rollout history dc/packit-service [--revision=X]`.

It's more tricky in case of `StatefulSet` which we use for worker.
`oc rollout undo` does not seem to work with `StatefulSet`
(even it [should](https://github.com/kubernetes/kubernetes/pull/49674)).
So when you happen to deploy broken worker and you want to revert/undo it
because you don't know what's the cause/fix yet, you have to:

1. `oc describe is/packit-worker` - select older image
2. `oc tag --source=docker usercont/packit-service-worker@sha256:<older-hash> myproject/packit-worker:<deployment>`
   And see the `packit-worker-x` pods being re-deployed from the older image.

### Prod re-deployment

1. Build base [packit image](https://hub.docker.com/repository/docker/usercont/packit):

- [move packit's `stable` branch to newer commit](#production-vs-staging-images)
- [WAIT for the image to be built successfully](https://hub.docker.com/repository/registry-1.docker.io/usercont/packit/timeline) - REALLY, don't proceed to the next step until this is built

2. Build service, worker, listeners and dashboard images

- you REALLY HAVE TO WAIT for the [base image](https://hub.docker.com/repository/registry-1.docker.io/usercont/packit/timeline) above to be built first
- move `packit-service`'s `stable` branch to newer commit
- move `packit-service-fedmsg`'s `stable` branch to newer commit
- move `dashboard`'s `stable` branch to newer commit
- move `packit-service-centosmsg`'s `stable` branch to newer commit
- move `sandcastle`'s `stable` branch to newer commit
- WAIT for [service](https://hub.docker.com/repository/docker/usercont/packit-service) and [worker](https://hub.docker.com/repository/docker/usercont/packit-service-worker) images to be built successfully
- WAIT for the [fedmsg listener](https://hub.docker.com/repository/docker/usercont/packit-service-fedmsg) to be built successfully
- WAIT for the [dashboard
  image](https://hub.docker.com/repository/docker/usercont/packit-dashboard) to be built successfully
- WAIT for the [centosmsg listener](https://hub.docker.com/repository/docker/usercont/packit-service-centosmsg) to be built successfully
- WAIT for the [sandcastle image](https://hub.docker.com/repository/docker/usercont/sandcastle) to be built successfully

3. Import images -> re-deploy

- If you don't want to wait for [it to be done automatically](#continuous-deployment) you can [do that manually](#manually-import-a-newer-image)

### How do I test my changes?

#### docker-compose (quick & dirty)

There's a [docker-compose.yml in packit-service](https://github.com/packit-service/packit-service/blob/master/docker-compose.yml).
See [Running packit-service locally](https://github.com/packit-service/packit-service/blob/master/CONTRIBUTING.md#running-packit-service-locally) for how to make that work.

#### oc cluster up (slow & better)

Because we run the service in OpenShift the more reliable way to test it
is to run an Openshift cluster locally and deploy the service there.
`oc cluster up` spawns the Openshift cluster.
Create `secrets/dev/` (steal them from our secret repo).
`cd vars; cp dev_template.yml dev.yml` and in `dev.yml` set `api_key` to the output of `oc whoami -t`.

Run `DEPLOYMENT=dev make deploy`.
That will also push locally built images (`:dev`) into the cluster's registry.

#### Staging (quick & reliable & but don't break it)

If you're lazy and you're sure your changes won't do any harm, you can temporarily get hold of staging instance for that.
Just build & push `packit-service-worker` and you can play.

- in packit: `make image`
- in packit-service:
  - `make worker`
  - `docker tag docker.io/usercont/packit-service-worker:dev docker.io/usercont/packit-service-worker:stg`
  - `docker push docker.io/usercont/packit-service-worker:stg`
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

We have to encrypt the secrets, because we are using them in Zuul CI. This repository provides helpful playbook to do this with one command:

```
DEPLOYMENT=stg make zuul-secrets
```

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

In case procedure bellow will not work, previously used http challenge can be used instead [link](https://github.com/packit-service/deployment/blob/008f5eaad69a620c54784f1fc19c7c775af9ec7d/README.md#obtaining-a-lets-encrypt-cert-using-certbot).
Be aware that http challenge approach is more complex, includes destructive actions and longer downtime.

TL;DR

1. Check prerequisites.
2. Run certbot to obtain the challenges.
3. Configure DNS TXT records based on values requested in 2.
4. Update secrets repository.
5. Re-deploy stg&prod.

_Note: If certbot was excuted against multiple domains you will repeat step 3. for each domain._

### 1. Prerequisites

Make sure the DNS is all set up:

```
$ dig prod.packit.dev
; <<>> DiG 9.11.5-P4-RedHat-9.11.5-4.P4.fc29 <<>> prod.packit.dev +nostats +nocomments +nocmd
;; global options: +cmd
;prod.packit.dev.               IN      A
prod.packit.dev.        2932    IN      CNAME   elb.e4ff.pro-eu-west-1.openshiftapps.com.
elb.e4ff.pro-eu-west-1.openshiftapps.com. 2932 IN CNAME pro-eu-west-1-infra-1781350677.eu-west-1.elb.amazonaws.com.
pro-eu-west-1-infra-1781350677.eu-west-1.elb.amazonaws.com. 60 IN A 52.30.203.240
pro-eu-west-1-infra-1781350677.eu-west-1.elb.amazonaws.com. 60 IN A 52.50.44.252
```

Check if you have access to packit.dev domain in [Google Domains](https://domains.google.com/m/registrar/packit.dev).

Check/install [certbot](https://certbot.eff.org/all-instructions) locally.

### 2. Run certbot to obtain the challenges.

Run certbot:

```
certbot certonly --config-dir ~/.certbot --work-dir ~/.certbot --logs-dir ~/.certbot --manual --preferred-challenges dns --email user-cont-team@redhat.com -d *.packit.dev -d *.prod.packit.dev -d *.stg.packit.dev
```

You will be asked to set TXT record for every domain requested:

```
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
Please deploy a DNS TXT record under the name
_acme-challenge.prod.packit.dev with the following value:

123456abcdef

Before continuing, verify the record is deployed.
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
Press Enter to Continue
```

### 3. Update DNS record

Go to [Google Domains](https://domains.google.com/m/registrar/packit.dev/dns) and create/set the corresponding value: TXT record called \_acme-challenge/\_acme-challenge.prod/\_acme-challenge.stg

Wait till is distributed - in another terminal check with:

```
nslookup -q=TXT _acme-challenge.prod.packit.dev
```

once it returns the configured value

```
[~/]$ nslookup -q=TXT _acme-challenge.packit.dev
Server:         213.46.172.37
Address:        213.46.172.37#53

Non-authoritative answer:
_acme-challenge.packit.dev      text = "123456abcdef"

Authoritative answers can be found from:

[~/]$ ping dashboard.packit.dev
```

Go to the terminal with certbot command waiting for your action and hit Enter.

Repeat this for all requested domains.

Once finished copy certificates to secrets repository (prod&stg)

```
cp /var/tmp/live/packit.dev/{fullchain,privkey}.pem _path_to_prod_secrets_
cp /var/tmp/live/packit.dev/{fullchain,privkey}.pem _path_to_stg_secrets_
```

### 4. Update secret repository

- push new branch and merge.

### 5.Re-deploy stg and prod environment:

```
DEPLOYMENT=stg make deploy
DEPLOYMENT=prod make deploy
```

Docs: https://certbot.eff.org/docs/using.html#manual

### How to test the TLS deployment

If you want to inspect local certificates, you can use `certtool` (`gnutls-utils` package) to view the cert's metadata:

```
$ certtool -i <fullchain.pem
X.509 Certificate Information:
        Version: 3
        Serial Number (hex): 04388dc3bcaaf649c1e891d130dfaf2aeedd
        Issuer: CN=Let's Encrypt Authority X3,O=Let's Encrypt,C=US
        Validity:
                Not Before: Thu Jul 11 07:13:42 UTC 2019
                Not After: Wed Oct 09 07:13:42 UTC 2019
```
