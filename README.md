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

You don't need to redeploy the whole stack, it is just enough to rollout a new image of the specific component (usually worker):
```
$ oc rollout latest dc/packit-service-worker
```
