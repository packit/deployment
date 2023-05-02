# Secrets

During deployment (`make deploy`), secret files are downloaded from a vault
into one of the subdirectories and transformed into Kubernetes/Openshift secrets.
They can also be downloaded independently with `make download-secrets`.
By default, these subdirectories contain only templates, which don't contain any secret,
but which are processes and injected with secrets during the deployment process.
If you want to see them rendered before you run the deployment,
use `make render-secrets-from-templates`.

## Install `bw` CLI

https://bitwarden.com/help/cli/#download-and-install

## Update secrets in Bitwarden

Use `scripts/update_bw_secret.sh` to update secrets, and don't have to click
through the Bitwarden Web UI, deleting and uploading attachments.

Here is the workflow how to do that:

1. Make sure your local copy is up-to-date. For example:

   ```
   $ SERVICE=packit DEPLOYMENT=stg make download-secrets
   ```

2. Edit the secret file you want to update, for example:

   ```
   $ $EDITOR secrets/packit/stg/extra-vars.yml
   ```

3. Update the secret in Bitwarden. For example:

   ```
   $ ./scripts/update_bw_secret.sh secrets/packit/stg/extra-vars.yml
   ```

The script figures out which Bitwarden item to edit from the path to the file,
so that needs to be provided as `secrets/<service>/<deployment>/<file>`.

Nothing happens if the file did not change. The script also helps with
updating the `! Changelog !`: saves the note in a file, opens the file with
`$EDITOR` to be edited, and updates the note in Bitwarden.

## Update secrets in OpenShift

Use `scripts/update_oc_secret.sh` to update secrets directly in OpenShift from
the command-line.

1. First make sure the local copies of the secrets are in sync
   with what's stored in Bitwarden. For example:

   ```
   $ SERVICE=packit DEPLOYMENT=stg make download-secrets
   ```

2. Edit the file you want to update. For example:

   ```
   $ $EDITOR secrets/packit/stg/packit-service.yaml.j2
   ```

3. Render secret files from the templates:

   ```
   $ SERVICE=packit DEPLOYMENT=stg make render-secrets-from-templates
   ```

   This creates `packit-service.yaml` from `packit-service.yaml.j2`
   (no secret values, stored in public repo) and `extra-vars.yml`
   (secret values, downloaded from the vault).

4. Login to OpenShift and select the right project. For example:

   ```
   $ oc login ...
   $ oc project packit-stg
   ```

5. Update the secret in OpenShift with the content of the file. You'll need to
   know the name of the secret. For example:

   ```
   $ scripts/update_oc_secret.sh packit-config secrets/packit/stg/packit-service.yaml
   ```

Don't forget that you'll need to re-spin the pods using the secret, so that
they pick up the change.

## What secret files the deployment expects

Not all services expect all of them. For example source-git services don't need `copr` & `private-key.pem`.
Check [generate-secrets role](../roles/generate-secrets/files) to see some pre-filled.

- `copr` - Your copr credentials.
- `extra-vars.yml` - tokens, passwords, keys, etc.
- `fedora.keytab` - Fedora kerberos.
- `fedora.toml` - [fedora-messaging configuration](https://fedora-messaging.readthedocs.io/en/stable/configuration.html).
- `fullchain.pem` & `privkey.pem`- Let's encrypt TLS certs.
- `id_ed25519[.pub]` - SSH keys, to push to a git forge.
- `packit-service.yaml.j2` - Template for the service/bot configuration with secret values to be taken from `extra-vars.yml`.
- `private-key.pem` - Specified in a GitHub App settings. Used to [sign access token requests](https://developer.github.com/apps/building-github-apps/authenticating-with-github-apps/#authenticating-as-a-github-app).
- `ssh_config` - SSH configuration to be able to run fedpkg inside the OpenShift pod.

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

- `packit-service.yaml.j2`:
  - `deployment: stg` -> `deployment: dev`
  - `fas_user: packit` -> `fas_user: your-fas-username`
  - `validate_webhooks: true` -> `validate_webhooks: false`
  - `server_name: stg.packit.dev` -> `server_name: service.localhost:8443`
- `extra-vars.yml`
  - would be nice to use your tokens/api keys in `packit_service.authentication`, but it's not crucial since it's for staging instances
  - `sentry.dsn`: just empty it to not send your devel bugs to Sentry
- `copr`: would be nice to use [your own token](https://copr.fedorainfracloud.org/api/) if you're planning to build in Copr
- `fedora.toml`: there's (2x) unique queue uuid which needs to be replaced with a new generated (`uuidgen`) one
  (if you'll run [fedmsg](https://github.com/packit/packit-service-fedmsg))
- `id_ed25519[.pub]`: replace with your ssh keys

Not all services use all of them. For example `copr` is needed only by `packit` service.
