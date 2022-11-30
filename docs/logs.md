## [Logs aggregation](https://github.com/packit/research/tree/main/logs-aggregation)

Each worker pod has a sidecar container running [Fluentd](https://docs.fluentd.org),
which is a data collector allowing us to get the logs from a worker via
[syslog](https://docs.fluentd.org/input/syslog) and send them to Splunk.

We use [our fluentd-splunk-hec image](https://quay.io/repository/packit/fluentd-splunk-hec),
built via [a workflow](https://github.com/packit/fluent-plugin-splunk-hec/blob/main/.github/workflows/rebuild-and-push-image.yml)
because we don't want to use [docker.io/splunk/fluentd-hec image](https://hub.docker.com/r/splunk/fluentd-hec).

### Where do I find the logs?

First, you have to [get access to Splunk](https://source.redhat.com/departments/it/splunk/splunk_wiki/faq#jive_content_id_How_do_I_request_access_to_Splunk)
(CMDB ID is 'PCKT-002').

Then go to https://rhcorporate.splunkcloud.com -> `Search & Reporting`

[The more specific search, the faster it'll be](https://source.redhat.com/departments/it/splunk/splunk_wiki/splunk_training_search_best_practices#jive_content_id_Be_more_specific).
At least, specify `index`, `source` and `msgid`.
You can start with [this search ](https://rhcorporate.splunkcloud.com/en-US/app/search/search?q=search%20index%3Drh_linux%20source%3Dsyslog%20msgid%3Dpackit-prod)
and tune it from there.
For example:

- change `msgid=packit-prod` to service instance you want to see logs from, e.g. to `msgid=packit-stg` or `msgid=stream-prod`
- add `| search message!="pidbox*"` to remove the ["pidbox received method" message which Celery pollutes the log with](https://stackoverflow.com/questions/43633914/pidbox-received-method-enable-events-reply-tonone-ticketnone-in-django-cel)
- add `| reverse` if you want to se the results from oldest to newest
- add `| fields _time, message | fields - _raw` to leave only time and message fields

All in one URL [here](https://rhcorporate.splunkcloud.com/en-US/app/search/search?q=search%20index%3Drh_linux%20source%3Dsyslog%20msgid%3Dpackit-prod%20%7C%20search%20message!%3D%22pidbox*%22%20%7C%20reverse%20%7C%20fields%20_time%2C%20message%20%7C%20fields%20-%20_raw) -
now just export it to csv; and you have almost the same log file
as you'd get by exporting logs from a worker pod.

For more info, see (Red Hat internal):

- [demo](https://drive.google.com/file/d/15BIsRl7fP9bPdyLBQvoljF2yHy52ZqHm)
- [Splunk wiki @ Source](https://source.redhat.com/departments/it/splunk)

### Debugging

To see the sidecar container logs, select a worker pod -> `Logs` -> `fluentd-sidecar`.

To [manually send some event to Splunk](https://docs.splunk.com/Documentation/SplunkCloud/8.2.2203/Data/UsetheHTTPEventCollector#Send_data_to_HTTP_Event_Collector)
try this (get the host & token from Bitwarden):

    $ curl -v "https://${SPLUNK_HEC_HOST}:443/services/collector/event" \
           -H "Authorization: Splunk ${SPLUNK_HEC_TOKEN}" \
           -d '{"event": "jpopelkastest"}'
