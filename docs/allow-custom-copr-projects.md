# Configure projects to be built in custom Copr repositories

By default, Packit builds PRs in its own namespace in Copr. It's possible
though to configure it to use a dedicated Copr repository by setting a
`project` and an `owner` config value.

But Packit should build only the allowed GitHub projects in these Copr
repositories. As a temporary solution, the mapping of Copr repositories to
GitHub projects is configured in the service configuration in
`packit-service.yaml`, using the `allowed_forge_projects_for_copr_project`
key.

Bellow are the steps to update this configuration when a user asks for some
GitHub projects to be allowed to build in a Copr repo.

## 1. Check that the request is legitimate

The user doing the request should be the owner of the Copr repository, or they
should be a member of the group owning the Copr repo.

The user doing the request should already have commits in the `main` branch of
the GitHub projects they are referring to.

If mapping the users chat handle or email address to their Fedora Account or
GitHub account is not unequivocal, send them a GPG encrypted message using
their SSH key in Fedora Accounts, and ask them to decrypt it and tell you the
content of it, in order to make sure that things fit.

If you have doubts with the above, ask for help :-)

## 2. Update the service config in stage

Although this might be not strictly required (Packit Stage might not be
enabled for the projects you are going to add), it's a good exercise to make
sure you are doing everything right.

1. Download the latest secrets from Bitwarden. In `packit/deployment` run:

   ```
   $ SERVICE=packit DEPLOYMENT=stg make download-secrets
   ```

2. Edit `packit-service.yaml.j2` and add the new mapping.

   ```
   $ $EDITOR secrets/packit/stg/packit-service.yaml.j2
   ```

   In case of group owned Copr repos the change is going to look like this:

   ```yaml
   allowed_forge_projects_for_copr_project:
     "@<group>/<repo>":
       - github.com/<namespace>/<project>
   ```

   For Copr repos owned by individuals:

   ```yaml
   allowed_forge_projects_for_copr_project:
     "<user>/<repo>":
       - github.com/<namespace>/<project1>
       - github.com/<namespace>/<project2>
   ```

   There can be multiple GitHub projects allowed to be built in the same Copr
   repo.

   Render `packit-service.yaml` from the template:

   ```shell
   $ SERVICE=packit DEPLOYMENT=stg make render-secrets-from-templates
   ```

   Test that it is a valid YAML. Use Python or
   [yq](https://github.com/mikefarah/yq) for this.

3. Login to the stage cluster and select the stage namespace:

   ```
   $ oc login ...
   $ oc project packit-stg
   ```

4. Update the OpenShift secret:

   ```
   $ scripts/update_oc_secret.sh packit-config secrets/packit/stg/packit-service.yaml
   ```

5. Re-spin all the worker pods to pick up the change, by first scaling the
   stateful sets to 0 replicas, and then scaling them back to the original
   number.

   To check the current worker stateful sets, run `oc get sts`.

   Scale to 0: `oc scale sts/packit-worker --replicas=0`. Wait till there are
   0 replicas ready.

   Scale back: `oc scale sts/packit-worker --replicas=1`.

   Check that all worker pods are running okay, and there are no errors in the
   logs.

## 3. Update the service config in prod

This is the same as doing it in stage, just replace `stg` with `prod`.

In prod there might be more types of workers (`packit-worker-short-running`,
`packit-worker-long-running`). All of them need to be respinned.

## 4. Let the user know that the change was made

And ask them to confirm that things are working.
