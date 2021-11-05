## Packit-service validation

For the validation of the packit-service we run a validation script every night.

Currently this is deployed in [Open PaaS](https://open.paas.redhat.com/console/project/packit-service-validation/overview).

[Cron job](./openshift/job-run-validation.yaml) - job for running of the validation script

[Containerfile](./Containerfile) - image used by the job

[packit-service-validation.py](./packit-service-validation.py) - script in the image

The script verifies that Copr builds and Testing farm runs are processed correctly for pull requests in `packit/hello-world` repo:

- comment trigger (each PR with title beginning `Basic test case:` is taken
  and commented with `/packit build`)
- commit (push) trigger - PR with title `Basic test case - commit trigger` is taken and a new empty commit is pushed
- opened PR trigger - new PR is created, the branch `test_case_opened_pr` is used as a source branch,
  after running the test the PR is closed

If you want to run the script on your own:

- Set a `GITHUB_TOKEN` environment variable holding a [personal access
  token](https://github.com/settings/tokens) with _public_repo_ scope.
- Have a [copr configuration file](https://copr.fedorainfracloud.org/api/) at
  `~/.config/copr`.
- Optionally, set a `SENTRY_SECRET` environment variable if you want to send
  the validation failures to Sentry.
