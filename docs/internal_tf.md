# Approve a project for using internal Testing Farm ranch

Add the project namespace to the `enabled_projects_for_internal_tf` list in [secrets/packit/prod/packit-service.yaml.j2](https://github.com/packit/deployment/blob/main/secrets/packit/prod/packit-service.yaml.j2)

Changes in config won't land automatically in production, you also need to [update the config manually with our script](https://github.com/packit/deployment/tree/main/secrets#update-secrets-in-openshift) or via [Web Console](https://console-openshift-console.apps.auto-prod.gi0n.p1.openshiftapps.com/k8s/ns/packit-prod/secrets/packit-config) and restart all the services:

    oc rollout restart deploy/packit-service
    oc rollout restart sts/packit-worker-short-running
    oc rollout restart sts/packit-worker-long-running

To list all workflows:

    oc get deploy
    oc get sts
