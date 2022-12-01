## Packit-service validation

For the validation of the packit-service we run a validation script every night.

The script verifies that Copr builds and Testing farm runs are processed correctly for pull requests in `packit/hello-world` repo:

- comment trigger (each PR with title beginning `Basic test case:` is taken
  and commented with `/packit build`)
- commit (push) trigger - PR with title `Basic test case - commit trigger` is taken and a new empty commit is pushed
- opened PR trigger - new PR is created, the branch `test_case_opened_pr` is used as a source branch,
  after running the test the PR is closed

## Deployment

The image is build via a [GitHub workflow](../../.github/workflows/build-and-push-cronjob-image.yaml)
and pushed to a [Quay.io repository](https://quay.io/repository/packit/packit-service-validation).

There is a [Helm Chart](https://github.com/packit/helm/tree/main/helm-charts/packit-service-validation)
and a CI/CD in [Gitlab repo](https://gitlab.cee.redhat.com/packit/validation-cronjob-script-deployment)
(internal because PSI is also internal) which installs/upgrades the chart to the
`cyborg` project in [PSI](https://ocp4.psi.redhat.com) on every push.
You just have to update the [image tag](https://quay.io/repository/packit/packit-service-validation?tab=tags)
in [production.yaml](https://gitlab.cee.redhat.com/packit/validation-cronjob-script-deployment/-/blob/main/production.yaml)
and/or [staging.yaml](https://gitlab.cee.redhat.com/packit/validation-cronjob-script-deployment/-/blob/main/staging.yaml).

## Running manually

If you want to run the script on your own:

- Set a `GITHUB_TOKEN` environment variable holding a [personal access
  token](https://github.com/settings/tokens) with _public_repo_ scope.
- Optionally, set a `SENTRY_SECRET` environment variable if you want to send
  the validation failures to Sentry.
