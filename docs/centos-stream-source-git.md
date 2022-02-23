## CentOS Stream source-git bot deployment specifics

### Production

Production instance runs in stream-prod project @ auto-prod cluster.
It serves [redhat/centos-stream/src/ repos](https://gitlab.com/redhat/centos-stream/src/).
A group webhook is set to send "Merge request events" to [API](https://prod.stream.packit.dev/api/webhooks/gitlab).

Example MRs:
[dist-git MR](https://gitlab.com/redhat/centos-stream/rpms/luksmeta/-/merge_requests/6)
created from a
[source-git MR](https://gitlab.com/redhat/centos-stream/src/luksmeta/-/merge_requests/6).

### Staging

Staging instance runs in stream-stg project @ auto-test cluster
([API](https://stg.stream.packit.dev/api/)) and is used to serve some
repos in our [packit-service/src/ namespace](https://gitlab.com/packit-service/src).
Because we can't use Group Webhooks there to set up the service for whole namespace
currently only some repos are served:

for example:

- open-vm-tools: [source-git MR](https://gitlab.com/packit-service/src/open-vm-tools/-/merge_requests/8) -> [dist-git MR](https://gitlab.com/packit-service/rpms/open-vm-tools/-/merge_requests/18)
- luksmeta: [source-git MR](https://gitlab.com/packit-service/src/luksmeta/-/merge_requests/2) -> [dist-git MR](https://gitlab.com/packit-service/rpms/luksmeta/-/merge_requests/2)
- glibc

There are actually real staging src-git and dist-git repos in [redhat/centos-stream/staging namespace](https://gitlab.com/redhat/centos-stream/staging)
but we haven't used them yet, because the CI (Pipelines) there don't seem to work the same way as in prod repos
so we use repos in our namespace (see above) because we have at least full control over them.

[gitlab_webhook.py](https://github.com/packit/deployment/blob/main/scripts/gitlab_webhook.py)
can be used to generate secret tokens to be used for setting up webhooks.

#### CI @ staging

In order for us to be able to experiment with syncing CI results from a dist-git MR back to a source-git MR,
we have a fake CI setup.
There's a `.gitlab-ci.yml` stored in both, the source-git and dist-git repos served by the staging service.
In a source-git repo it's in `.distro/` ([example](https://gitlab.com/packit-service/src/open-vm-tools/-/blob/c9s/.distro/.gitlab-ci.yml))
and before the service creates a dist-git MR from a source-git MR the file is synced into the dist-git repo.
Once the dist-git MR is created the pipeline is run based on the file and the results are seen in the dist-git MR.
It's stored also in the dist-git repo ([example](https://gitlab.com/packit-service/rpms/open-vm-tools/-/blob/c9s/.gitlab-ci.yml)),
so that the file is not in a diff of a newly created dist-git MR as a newly added file.

### Syncing dist-git MR CI results back to a src-git MR

#### prod

The notification about a change of a pipeline's status is sent to a group webhook (with "Pipeline events" trigger)
which is manually added to the [redhat/centos-stream/rpms group](https://gitlab.com/redhat/centos-stream/rpms).

#### staging

For staging, a project webhook is added to forks in [packit-as-a-service-stg namespace](https://gitlab.com/packit-as-a-service-stg),
because that's where a pipeline runs in case of non-premium plan (packit-service/rpms/ namespace).