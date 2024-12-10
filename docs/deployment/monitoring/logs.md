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

You should be able to see production logs using [this query](https://rhcorporate.splunkcloud.com/en-US/app/search/search?q=search%20index%3D"rh_paas"%20kubernetes.namespace_name%3D"packit--prod"):

    index="rh_paas" kubernetes.namespace_name="packit--prod"

and staging logs using [this query](https://rhcorporate.splunkcloud.com/en-US/app/search/search?q=search%20index%3D"rh_paas_preprod"%20kubernetes.namespace_name%3D"packit--stg"):

    index="rh_paas_preprod" kubernetes.namespace_name="packit--stg"

If the above query doesn't return any results, [request access](https://source.redhat.com/departments/it/splunk/splunk_wiki/faq#jive_content_id_How_do_I_request_access_to_additional_data_sets_in_Splunk) to `rh_paas` index.

:::caution

If you cannot see _Access to Additional Datasets_ (as suggested by the instructions), use _Update Permissions_ as the _Request Type_ and ask to access the `rh_paas` index in the additional details.

:::

[The more specific search, the faster it'll be](https://source.redhat.com/departments/it/splunk/splunk_wiki/splunk_training_search_best_practices#jive_content_id_Be_more_specific).
You should specify at least `index` and `kubernetes.namespace_name`, but if you want to export the results then you'll have to exclude the `_raw` field containing the complete JSON structure and include only fields you need, such as `message` or `kubernetes.pod_name`, otherwise you'll most likely hit quota.
You can start with the examples above and tune it from there.
For example:

- add `| reverse` if you want to se the results from oldest to newest
- add `| fields - _time, _raw | fields message` to leave only message field without timestamp duplication

All in one URL [here](https://rhcorporate.splunkcloud.com/en-US/app/search/search?q=search%20index%3D%22rh_paas%22%20kubernetes.namespace_name%3D%22packit--prod%22%20%7C%20fields%20-%20_time%2C%20_raw%20%7C%20fields%20message%20%7C%20reverse) - now just export it to csv; and you have almost the same log file
as you'd get by exporting logs from a worker pod.

For more info, see (Red Hat internal):

- [demo](https://drive.google.com/file/d/15BIsRl7fP9bPdyLBQvoljF2yHy52ZqHm)
- [Splunk wiki @ Source](https://source.redhat.com/departments/it/splunk)
- [Searching Logs in Splunk using Unified Logging @ Source](https://source.redhat.com/departments/it/datacenter_infrastructure/itcloudservices/itocp/itocp_wiki/searching_logs_in_splunk_using_unified_logging)
