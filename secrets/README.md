## Secrets

Deployment process (`make deploy`) expects files to be transformed to
Openshift secrets to be found in these subdirectories.
These files are either automatically downloaded (`make download-secrets`)
or they need to be created manually in case of local/dev/test deployment.

## What secret files the deployment expects

Some of them are pre-filled in the [template](/secrets/template) directory.

- `copr` - Your copr credentials. See pre-filled template in [templates directory](/secrets/template/copr).
- `extra-vars.yml` - Secrets for Postgresql & Redis.
- `fedora.keytab` - Fedora kerberos.
- `fedora.toml` - [fedora-messaging configuration](https://fedora-messaging.readthedocs.io/en/stable/configuration.html).
- `fullchain.pem` & `privkey.pem`- Let's encrypt TLS certs.
- `id_rsa[.pub]` - SSH keys, to push to a git forge.
- `packit-service.yaml` - Configuration for Packit as a service. See pre-filled template in [templates directory](/secrets/template/packit-service.yaml).
- `private-key.pem` - Specified in a Github App settings. Used to [sign access token requests](https://developer.github.com/apps/building-github-apps/authenticating-with-github-apps/#authenticating-as-a-github-app).
- `sentry_key` - Sentry DSN.
- `ssh_config` - SSH configuration to be able to run fedpkg inside of the OpenShift pod. See pre-filled template in [templates directory](/secrets/template/ssh_config).

Not all services expect all of them. For example source-git services don't need `copr` & `private-key.pem`.
