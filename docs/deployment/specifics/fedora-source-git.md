---
title: Fedora Source-git
---

# Fedora Source-git Bot Deployment Specifics

## Production

Production instance runs in `fedora-source-git-prod` project @ `auto-prod` cluster.
It serves [`fedora/src/` repos](https://gitlab.com/fedora/src/).
A group webhook is set to send "Merge request events" to [API](https://prod.fedora-source-git.packit.dev/api/webhooks/gitlab).

Example:
[dist-git MR](https://src.fedoraproject.org/rpms/python-httpretty/pull-request/19)
created from a
[source-git MR](https://gitlab.com/fedora/src/python-httpretty/-/merge_requests/2).

## Staging

There's no staging instance yet.
