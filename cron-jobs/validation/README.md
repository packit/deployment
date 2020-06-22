## Packit-service validation

For the validation of the packit-service we run a validation script every night.

[Cron job](./openshift/job-run-validation.yaml) - job for running of the validation script

[Dockerfile](./Dockerfile) - image used by the job

[packit-service-validation.py](./packit-service-validation.py) - script in the image

If you want to run the script on your own, everything you need is to set some env vars - GITHUB_TOKEN
and optionally SENTRY_SECRET, if you want to send the validation failures to Sentry
(if not, you can just comment out the 2 Sentry lines and print the failure messages instead of
sending them to Sentry) and have a copr configuration file in your ~/.config directory.
