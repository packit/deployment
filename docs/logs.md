## [Logs aggregation](https://github.com/packit/research/tree/main/logs-aggregation)

When a worker pod is restarted (due to image or cluster update), the pod logs are gone.
To work around this, each worker pod has a sidecar container which runs [Fluentd](https://docs.fluentd.org).
Fluentd is a data collector which allows us to get the logs from a worker via
[syslog](https://docs.fluentd.org/input/syslog) and send them someplace to be stored permanently.
Currently, until we figure out how to send the logs to Splunk,
we're [sending them to files](https://docs.fluentd.org/output/file) in a persistent volume mount to
`/var/log/packit/` in the fluentd container.

We use [our fluentd-splunk-hec image](https://quay.io/repository/packit/fluentd-splunk-hec),
built via [a workflow](https://github.com/jpopelka/fluent-plugin-splunk-hec/blob/main/.github/workflows/rebuild-and-push-image.yml)
because we don't want to use [docker.io/splunk/fluentd-hec image](https://hub.docker.com/r/splunk/fluentd-hec).

### Where do I find the logs?

Select a worker pod -> `Terminal` -> `fluentd sidecar`

    $ cd /var/log/packit
    $ ls -lah
    $ gzip -d .20221006_0.log.gz
    $ less .20221006_0.log

You can see also a `buffer.*.log` file which contains today's logs.
It'll be flushed and compressed into a permanent gzip file at the end of the day.

### What is missing?

The format of the log files is not much readable as it contains all the info from syslog.
Eventually, we want to send the logs to Splunk.
Until then, it can happen that the (1Gi) space on the permanent volumes gets depleted.
To delete old (>7d) log files, run `find /var/log/packit -mtime +7 -delete`.
