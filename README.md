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

You have to copy it to `prod.yml` or `stg.yml`
depending on what environment you want to deploy to.

If you want to deploy to 'production environment', you `cp template.yml prod.yml`
and in `prod.yml` you set `host: your-production-cluster-url`.
Then you run `DEPLOYMENT=prod make deploy`.

The ansible playbook then includes one of the variable files depending on the
value of DEPLOYMENT environment variable and processes all the templates with
variables defined in the file.

If you want to remove all objects from the deployment (project) run e.g.
`DEPLOYMENT=stg make cleanup`.


## Local development in a local cluster

Create a new set of variables:
```
$ cp -av vars/{template,dev}.yml
```

And just deploy:
```
$ DEPLOYMENT=dev make deploy
```


### Updating

All our pods use images referenced to digests, e.g.

```
docker.io/usercont/packit-service@sha256:71b2ed8f1fb11d27eb3c8d1975237b05e8cd6a52b52ea1f80bf46e8dc21a0f16
```

If you want to update a deployment, just run `make deploy`. It may take a while for all the jobs to finish. Just have a coffee.


### Images

#### Service vs. service worker images
There are separate images for the [service / web server](https://hub.docker.com/r/usercont/packit-service) (which accepts requests) and for the [workers](https://hub.docker.com/r/usercont/packit-service-worker) (which do the actual work).

#### Production vs. Staging images

There are separate images for staging and production deployment.
Staging images are `:stg` tagged and built from `master` of `packit` and `packit-service`.
Production images are `:prod` tagged and built from `stable` branch of `packit` and `packit-service`.
To move `stable` branch to a newer 'stable' commit:
- git branch -f stable commit-hash
- git push [-u upstream] stable

Beware: [packit-service-worker image](https://cloud.docker.com/u/usercont/repository/docker/usercont/packit-service-worker) is not automatically rebuilt when its base [packit image](https://cloud.docker.com/u/usercont/repository/docker/usercont/packit) changes. You have to [trigger](https://cloud.docker.com/u/usercont/repository/docker/usercont/packit-service-worker/builds) the build manually.

### Revert a deployment

Since all our images now use digests - we reference to precise image and not to a "symlink", we can now easily revert deployments.

```
$ oc rollout undo sts/packit-worker
```

### Zuul

We have to encrypt the secrets, because we are using them in Zuul CI. This repository provides helpful playbook to do this with one command:
```
DEPLOYMENT=stg make zuul-secrets
```

## How are the secrets encrypted?

Zuul provides a public key for every project. The ansible playbook downloads Zuul repository and pass the project tenant and name as parameters to encryption script. This script then encypts files with public key of the project.
For more information please refer to [official docs](https://ansible.softwarefactory-project.io/docs/user/zuul_user.html#create-a-secret-to-be-used-in-jobs).

## Obtaining a Let's Encrypt cert using `certbot`

Please beer (Milk coffee stout) in mind this is the easiest process I was able
to figure out: there is a ton of places for improvements and ideally make it
automated 100%.

TL;DR

1. Deploy a certbot container in the project.
2. Use the manual challenge.
3. Run certbot and obtain the challenge.
4. Create a custom python2 ( :((( ) script and serve the secret.
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

And that openshift's router accepts it:
```
$ oc describe route.route.openshift.io/get-them-certs
Name:                   get-them-certs
Namespace:              packit-prod
Requested Host:         prod.packit.dev
                          exposed on router router (host elb.e4ff.pro-eu-west-1.openshiftapps.com) 10 minutes ago
```

### Just do it

Deploy the stuff to the cluster:
```
$ DEPLOYMENT=prod make get-certs
```

If there is packit-service deployed, we need to delete the route to free the host name `{{ deployment }}.packit.dev` for `get-them-certs`:
```
$ oc delete route.route.openshift.io/packit-service
```

Open two terminal sessions to the pod:
```
$ oc rsh pod/get-them-certs-1-b5h2h
```

Run `certbot` in one:
```
$ certbot --config-dir /tmp --work-dir /tmp --logs-dir /tmp certonly --manual --email user-cont-team@redhat.com -d prod.packit.dev
```
(`/tmp` is writable, the rest is not.)

Now we need to serve the challenge using the haxxx/serve-acme-challenge.py script:
```
$ python2 serve-acme-challenge.py /.well-known/acme-challenge/<secret> <secret-data>
```
(just copy the script in the pod)
Usage of the script is: `$ prog <PATH> <THE-SECRET>`.

Values of `<secret>` and `<secret-data>` are generated by cert-bot in the first terminal session.

And that's it! We got the certs now, let's get them from the pod to this git repo:
```
$ oc rsh pod/get-them-certs-1-wr42x cat /tmp/live/prod.packit.dev/cert.pem > cert.pem

$ oc rsh pod/get-them-certs-1-wr42x cat /tmp/live/prod.packit.dev/chain.pem > chain.pem

$ oc rsh pod/get-them-certs-1-wr42x cat /tmp/live/prod.packit.dev/fullchain.pem > fullchain.pem

$ oc rsh pod/get-them-certs-1-wr42x cat /tmp/live/prod.packit.dev/privkey.pem > privkey.pem
```

Don't forget to do cleanup:
```
oc delete all -l name=get-them-certs
oc delete all -l service=get-them-certs
```

And deploy the packit-service route back:
```
DEPLOYMENT=prod make deploy
```

Docs: https://certbot.eff.org/docs/using.html#manual

**Note:** If you want to make a production deployment with new secrets, the old ones can be deleted by running:
```
oc delete secrets --all
```

### How to test the TLS deployment

If you want to inspect local certificates, you can use `certtool` to view the cert's metadata:
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
`certtool` is included in gnutls-utils package.
