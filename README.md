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
If you want to re-deploy newer `packit` and/or `packit-service` code into prod, you first have to move `stable` branch(es) to a newer 'stable' commit and wait for Docker Hub to rebuild the images.
- git branch -f stable commit-hash
- git push [-u upstream] stable


### Revert a deployment

Since all our images now use digests - we reference to precise image and not to a "symlink", we can now easily revert deployments.

```
$ oc rollout undo sts/packit-worker
```
