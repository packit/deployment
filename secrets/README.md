## Secrets

Deployment process (`make deploy`) expects files to be transformed to
Openshift secrets to be found in these subdirectories.
These files are either automatically downloaded (`make download-secrets`)
or they need to be created manually in case of local/dev/test deployment.

## What secret files the deployment expects

Not all services expect all of them. For example source-git services don't need `copr` & `private-key.pem`.
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

## Running a service/bot locally

To deploy a {SERVICE} into your [local Openshift cluster](../docs/testing-changes.md),
run `SERVICE=the-service DEPLOYMENT=dev make deploy`.

Local deployment needs some secrets which can be obtained using the steps listed below:

- Create `dev` directory under `secrets/{SERVICE}/`
- Replace variables with your user specific values in `roles/generate-secrets/vars/main.yml`
- Generate the secrets either by running `make generate-local-secrets` or manually.

### How to populate {SERVICE}/dev/ manually

The easiest is to download `stg/` secrets (`DEPLOYMENT=stg make download-secrets`),
copy into `dev/` and do some tweaks there - like:

- `packit-service.yaml`:
  - `deployment: stg` -> `deployment: dev`
  - `fas_user: packit` -> `fas_user: your-fas-username`
  - `validate_webhooks: true` -> `validate_webhooks: false`
  - `server_name: stg.packit.dev` -> `server_name: service.localhost:8443`
  - would be nice to use your tokens/api keys in `authentication`, but it's not crucial since it's for staging instances
- `sentry_key`: just empty it to not send your devel bugs to Sentry
- `copr`: would be nice to use [your own token](https://copr.fedorainfracloud.org/api/) if you're planning to build in Copr
- `fedora.toml`: there's (2x) unique queue uuid which needs to be replaced with a new generated (`uuidgen`) one
  (if you'll run [fedmsg](https://github.com/packit/packit-service-fedmsg))
- `id_rsa[.pub]`: replace with your ssh keys

Not all services use all of them. For example `copr` is needed only by `packit` service.
