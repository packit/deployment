---
title: Logs
---

# Logs

See a research for [Logs aggregation](https://packit.dev/research/monitoring/logs-aggregation).

We are following the first solution described in this [document](https://source.redhat.com/departments/it/devit/it-infrastructure/itcloudservices/itocp/it_paas_kb/logging_to_splunk_on_managed_platform), _logging to stdout_ with no need for a forwarder sidecar pod.

## Where do I find the logs?

First, you have to [get access to Splunk](https://source.redhat.com/departments/it/splunk/splunk_wiki/faq#jive_content_id_How_do_I_request_access_to_Splunk)
(CMDB ID is 'PCKT-002').

Then go to https://rhcorporate.splunkcloud.com → `Search & Reporting`

You should be able to see some logs using [this query](https://rhcorporate.splunkcloud.com/en-US/app/search/search?q=search%20index%3D%22rh_paas%22%20source%3D%22%2Fvar%2Flog%2Fcontainers%2Fpackit-worker*.log"):

    index="rh_paas" source="/var/log/containers/packit-worker*.log"

If the above query doesn't return any results, [request access](https://source.redhat.com/departments/it/splunk/splunk_wiki/faq#jive_content_id_How_do_I_request_access_to_additional_data_sets_in_Splunk) to `rh_paas` index.

[The more specific search, the faster it'll be](https://source.redhat.com/departments/it/splunk/splunk_wiki/splunk_training_search_best_practices#jive_content_id_Be_more_specific).
At least, specify `index`, `source`.
You can start with [this search ](https://rhcorporate.splunkcloud.com/en-US/app/search/search?q=search%20index%3D%22rh_paas%22%20source%3D%22%2Fvar%2Flog%2Fcontainers%2Fpackit-worker*.log%22%20NOT%20pidbox)
and tune it from there.
For example:

- add `| reverse` if you want to se the results from oldest to newest
- add `| fields _raw | fields - _time` to leave only message field without timestamp duplication

All in one URL [here](https://rhcorporate.splunkcloud.com/en-US/app/search/search?q=search%20index%3D%22rh_paas%22%20source%3D%22%2Fvar%2Flog%2Fcontainers%2Fpackit-worker-short-running-0_packit--stg_packit-worker-*.log%22%20%7C%20fields%20_raw%20%7C%20fields%20-%20_time%20%7C%20reverse) - now just export it to csv; and you have almost the same log file
as you'd get by exporting logs from a worker pod.

For more info, see (Red Hat internal):

- [demo](https://drive.google.com/file/d/15BIsRl7fP9bPdyLBQvoljF2yHy52ZqHm)
- [Splunk wiki @ Source](https://source.redhat.com/departments/it/splunk)
