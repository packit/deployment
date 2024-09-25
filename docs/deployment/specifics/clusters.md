---
title: Clusters
---

## Automotive → MP+

Currently we are moving from the Automotive cluster to the MP+ cluster. Our
staging deployment is already present on the MP+ and there were some differences
introduced once the migration started.

### Namespaces

Previously we have used a rather simple `packit-{{ deployment }}` namespace. On
MP+ we are given `packit` as a tenant prefix, that needs to be separated from
our custom namespaces by `--`, therefore we use `packit--stg` and
`packit--stg-sandbox`.

### Postgres

On MP+ we have also moved to the newer postgres image, specifically we have used
v13 and moved on to the v15.

### Logging

On Automotive cluster we're using fluentd-sidecar to upload the logs to the
Splunk. Within the MP+ cluster we don't need to, since the logs can be output to
the `stdout` and are logged implicitly.

### Firewall

Outgoing connections on the MP+ are implicitly denied and firewall rules must be
explicitly requested. `10.0.0.0/8` network access from within our sandbox is
explicitly denied.

#### Requesting firewall rules

1. Search for “egress firewall rules OSD” on Source
2. Shiny link _opening a ticket_
3. You can take an inspiration from RITM1861658; almost all of our tickets for
   firewall rules follow the template below.

#### Template and notes

```
• source: ‹list the clusters here›
• destination: ‹list of domains›
• protocol: 80, 443
• justification: ‹almost as our release notes›
(N clusters × M domains × P ports)
```

If you want to include subdomains, I would recommend typing it as
`.example.com`, e.g. `.kde.org`.

Don't forget to replace the `N`, `M`, and `P` with their respective values, it
is used just as a check. You can also link the original issue with the waiting
list, not required though.

If you need to request outgoing SSH to be allowed (e.g. SSH access to git
forges), don't forget to specify port 22 (which is the usual default), **and**
instead of domain, give **IP addresses**. SSH access is bound by IPs rather than
domains (can be seen in the “inspiration” ticket mentioned above).
