## Packit-service validation

For the validation of the packit-service we run a validation script every night.

Currently this is deployed in the cyborg project in PSI.

[Cron job](./openshift/job-run-validation.yaml) - job for running of the validation script

[Containerfile](./Containerfile) - image used by the job

[packit-service-validation.py](./packit-service-validation.py) - script in the image

The script verifies that Copr builds and Testing farm runs are processed correctly for pull requests in `packit/hello-world` repo:

- comment trigger (each PR with title beginning `Basic test case:` is taken
  and commented with `/packit build`)
- commit (push) trigger - PR with title `Basic test case - commit trigger` is taken and a new empty commit is pushed
- opened PR trigger - new PR is created, the branch `test_case_opened_pr` is used as a source branch,
  after running the test the PR is closed

#### How to run the script

If you want to deploy the script:

- You have to have a directory with secrets and you need to define path to it [here](./openshift/job-run-validation.yaml)
  (by default `./secrets`).
- The directory with secrets needs to contain:
  - `github_token` - Github token for `usercont-release-bot` user
  - `secret_sentry` - Sentry key
- You have to define your Openshift API token [here](./openshift/job-run-validation.yaml).
- If you have everything prepared, you just need to run `DEPLOYMENT=production make deploy`
  or `DEPLOYMENT=staging make deploy` in this directory.

If you want to run the script on your own:

- Set a `GITHUB_TOKEN` environment variable holding a [personal access
  token](https://github.com/settings/tokens) with _public_repo_ scope.
- Optionally, set a `SENTRY_SECRET` environment variable if you want to send
  the validation failures to Sentry.
