# Ansible playbooks and scripts for deploying packit-service to Openshift

## tl;dr How to deploy

1. Obtain all the necessary [secrets](/secrets/README.md).
2. in [vars](vars/) copy [vars/template.yml](vars/template.yml) to `{deployment}.yml` where `{deployment}` is one of `prod` or `stg` and fill in values
3. `dnf install ansible origin-clients python3-openshift`
4. `DEPLOYMENT={deployment} make deploy`

## What's in here

- [playbooks](playbooks/) - Ansible playbooks.
- [vars](vars/) - Variable file(s). See section below for more info.
- [Openshift](openshift/) - Openshift resource configuration files (templates).
- [secrets](secrets/) - secret stuff to be used from `openshift/secret-*.yml.j2`

### Variable files

[vars/template.yml](vars/template.yml) is a variable file template.

You have to copy it to `prod.yml`, `stg.yml` or `dev.yml`
depending on what environment you want to deploy to.

#### Local development in a local cluster

For example if you want to deploy to 'devel environment', do
`cp template.yml dev.yml` and in `dev.yml` set `host:` and `api_key:`.
Then run `DEPLOYMENT=dev make deploy`.

The Ansible playbook then includes one of the variable files depending on the
value of DEPLOYMENT environment variable and processes all the templates with
variables defined in the file.

If you want to remove all objects from the deployment (project) run e.g.
`DEPLOYMENT=dev make cleanup`.

### Images

#### Service vs. worker images
There are separate images for
* [service / web server](https://hub.docker.com/r/usercont/packit-service) - accepts webhooks and tasks workers
* [fedora messaging consumer](https://hub.docker.com/r/usercont/packit-service-fedmsg) - listens on fedora messaging for events from Copr and tasks workers
* [workers](https://hub.docker.com/r/usercont/packit-service-worker) - do the actual work

#### Production vs. Staging images

Service and worker have separate images for staging and production deployment.
Staging images are `:stg` tagged and built from `master` of `packit` and `packit-service`.
Production images are `:prod` tagged and built from `stable` branch of `packit` and `packit-service`.
To move `stable` branch to a newer 'stable' commit:
- git branch -f stable commit-hash
- git push [-u upstream] stable

Beware: [packit-service-worker image](https://cloud.docker.com/u/usercont/repository/docker/usercont/packit-service-worker) is not automatically rebuilt when its base [packit image](https://cloud.docker.com/u/usercont/repository/docker/usercont/packit) changes. You have to [trigger](https://cloud.docker.com/u/usercont/repository/docker/usercont/packit-service-worker/builds) the build manually.

### DeploymentConfig vs. StatefulSet

[Service](openshift/deployment.yml.j2) and [service-fedmsg](openshift/deployment-fedmsg.yml.j2) are [DeploymentConfigs](https://docs.openshift.com/container-platform/3.11/dev_guide/deployments/how_deployments_work.html), but [worker](openshift/statefulset-worker.yml.j2) is a [StatefulSet](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset).

### Continuous Deployment

We use [ImageStreams](https://docs.openshift.com/container-platform/3.11/architecture/core_concepts/builds_and_image_streams.html#image-streams) as intermediary between an image registry and a Deployment. It has several significant benefits:
- We can automatically trigger Deployment when a new image is pushed to the registry.
- We can rollback/revert/undo the Deployment (previously we had to use image digests to achieve this).

There's a `continuous_deployment` variable in `vars/*.yaml` which says whether
we want to automatically/continuously re-deploy whenever a new image appears in
Docker Hub. It's `false` by default, but you should set it to `true` in your
`{dev|stg}.yaml`.

`Docker Hub` -> (stg:automatic / prod:manual)[1] -> `ImageStream` -> (automatic)[2] -> `DeploymentConfig`/`StatefulSet`

[1] set in ImageStream->spec->tags->importPolicy->scheduled
[2] set in DeploymentConfig->spec->triggers->imageChangeParams->automatic

Warn: OpenShift Online (where we currently run Packit Service) seems to have
turned off these periodical image registry to ImageStream updates even when
we explicitly [request them](https://docs.openshift.com/container-platform/3.11/architecture/core_concepts/builds_and_image_streams.html#image-stream-mappings-working-periodic).

To [manually update metadata in an ImageStream](https://docs.openshift.com/container-platform/3.11/dev_guide/managing_images.html#importing-tag-and-image-metadata) you can run
```
$ oc import-image is/packit-worker:<deployment>
```

### Rolling out new updates

* On staging everything should be automatic(, but it's not due to the above described OS Online issue).
* On prod you have to manually run `oc import-image is/packit-{service|service-fedmsg|worker}:<deployment>` once a new `:prod` image is pushed/built in Docker Hub.

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
And see the `packit-worker-x` pods beeing re-deployed from the older image.

## Zuul

We have to encrypt the secrets, because we are using them in Zuul CI. This repository provides helpful playbook to do this with one command:
```
DEPLOYMENT=stg make zuul-secrets
```

### How are the secrets encrypted?

Zuul provides a public key for every project. The ansible playbook downloads Zuul repository and pass the project tenant and name as parameters to encryption script. This script then encrypts files with public key of the project.
For more information please refer to [official docs](https://ansible.softwarefactory-project.io/docs/user/zuul_user.html#create-a-secret-to-be-used-in-jobs).


## Obtaining a Let's Encrypt cert using `certbot`

Please beer (Milk coffee stout) in mind this is the easiest process I was able
to figure out: there is a ton of places for improvements and ideally make it
automated 100%.

TL;DR

1. Deploy a certbot container in the project.
2. Use the manual challenge.
3. Run certbot and obtain the challenge.
4. Run a custom script and serve the secret.
5. Collect the certs and get that stout!

### Prep

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

### Just do it

Deploy the stuff to the cluster:
```
$ DEPLOYMENT=prod make get-certs
```

Verify the `get-them-certs` route exposes the `prod.packit.dev`:
```
$ oc describe route.route.openshift.io/get-them-certs
Name:                   get-them-certs
Namespace:              packit-prod
Requested Host:         prod.packit.dev
                          exposed on router router (host elb.e4ff.pro-eu-west-1.openshiftapps.com) 10 minutes ago
```

If there is `packit-service` deployed, you need to delete the route to free the host for `get-them-certs`:
```
$ oc delete route packit-service
```

Now, open two terminal sessions to the pod:
```
$ oc rsh pod/get-them-certs-1-abcde
```

Run `certbot` in one:
```
$ certbot certonly --config-dir /tmp --work-dir /tmp --logs-dir /tmp --manual --email user-cont-team@redhat.com -d prod.packit.dev
```
and answer questions until it tells you to create a file containing data **abc** and make it available on your web server at URL http://prod.packit.dev/.well-known/acme-challenge/xyz.

Now we need to serve the challenge using the [haxxx/serve-acme-challenge.py](./haxxx/serve-acme-challenge.py) script.
First, copy the script into the pod:
```
$ oc rsh get-them-certs-1-abcde mkdir /tmp/haxxx/

$ oc rsync haxxx/ get-them-certs-1-abcde:/tmp/haxxx/
```

In second terminal session:
```
$ cd /tmp/haxxx/
$ python3 serve-acme-challenge.py /.well-known/acme-challenge/xyz abc
```
Values of `<abc>` and `<xyz>` are generated by cert-bot in the first terminal session.

Return to first terminal and Press Enter to Continue.

And that's it! We got the certs now, let's get them from the pod to this git repo:
```
$ oc rsh pod/get-them-certs-1-abcde cat /tmp/live/prod.packit.dev/fullchain.pem | dos2unix > secrets/prod/fullchain.pem
$ oc rsh pod/get-them-certs-1-abcde cat /tmp/live/prod.packit.dev/privkey.pem | dos2unix > secrets/prod/privkey.pem
```
There are also `cert.pem` & `chain.pem` generated. You can copy them as well, but we don't need them at the moment.
The files that `oc rsh pod/x cat *.pem` returns contain `^M` characters, therefore we use `dos2unix` to [fix them](https://unix.stackexchange.com/questions/32001/what-is-m-and-how-do-i-get-rid-of-it). 

Don't forget to do cleanup:
```
$ oc delete all -l name=get-them-certs
$ oc delete all -l service=get-them-certs
```

And deploy the `packit-service` route back:
```
$ DEPLOYMENT=prod make deploy
```

Docs: https://certbot.eff.org/docs/using.html#manual

**Note:** If you want to make a production deployment with new secrets, the old ones can be deleted by running:
```
oc delete secrets --all
```

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
