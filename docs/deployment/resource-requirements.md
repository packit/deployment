---
title: Resource requirements
---

Usual Packit Service deployment consists of the following services with these
resource requirements.

## CPU requirements

| Deployment       |  Requested (always assigned) |  Limit |
| ---------------- | ---------------------------: | -----: |
| postgres         |                        `30m` |    `1` |
| redict           |                        `10m` |  `10m` |
| flower           |                         `5m` |  `50m` |
| nginx            |                         `5m` |  `10m` |
| pushgateway      |                         `5m` |  `10m` |
| tokman           | `20m` (prod, `5m` otherwise) |  `50m` |
| dashboard        |                         `5m` |  `50m` |
| fedmsg           |                         `5m` |  `50m` |
| beat             |                         `5m` |  `50m` |
| service          |                        `10m` | `200m` |
| worker (generic) |                       `100m` | `400m` |
| worker (short)   |                        `80m` | `400m` |
| worker (long)    |                       `100m` | `600m` |

## Memory requirements

| Deployment       |      Requested (always assigned) |                              Limit |
| ---------------- | -------------------------------: | ---------------------------------: |
| postgres         |  `1Gi` (prod, `256Mi` otherwise) | `1536Mi` (prod, `512Mi` otherwise) |
| redict           |                          `128Mi` |                            `256Mi` |
| flower           |                           `80Mi` |                            `128Mi` |
| nginx            |                            `8Mi` |                             `32Mi` |
| pushgateway      |                           `16Mi` |                             `32Mi` |
| tokman           | `100Mi` (prod, `88Mi` otherwise) |  `160Mi` (prod, `128Mi` otherwise) |
| dashboard        |                          `128Mi` |                            `256Mi` |
| fedmsg           |                           `88Mi` |                            `128Mi` |
| beat             |                          `160Mi` |                            `256Mi` |
| service          |                          `320Mi` |    `1Gi` (prod, `512Mi` otherwise) |
| worker (generic) |                          `384Mi` |                           `1024Mi` |
| worker (short)   |                          `320Mi` |                            `640Mi` |
| worker (long)    |                          `384Mi` |                           `1024Mi` |

## Currently allowed requirements / limits

| Resource | Allowed to request | Limit |
| -------- | -----------------: | ----: |
| CPU      |                `3` |  `12` |
| Memory   |              `6Gi` | `8Gi` |

## Total for production

| Deployment       | Memory request | Memory limit | CPU request |   CPU limit |
| ---------------- | -------------: | -----------: | ----------: | ----------: |
| non-scalable[^1] |       `2052Mi` |     `3808Mi` |      `100m` |     `1480m` |
| 2× short worker  |        `640Mi` |     `1280Mi` |      `160m` |      `800m` |
| 2× long worker   |        `768Mi` |     `2048Mi` |      `200m` |     `1200m` |
| **Σ**            |   **`3460Mi`** | **`7136Mi`** |  **`460m`** | **`3480m`** |

## Proposed changes

1. Revert to the pre-MP+ resources (they were higher for service, workers and
   postgres; lower values were used due to a hardcoded check in the templates);

   Pre-MP+ memory requirements/limits for production deployment:

   | Deployment | Requested | Limit |
   | ---------- | --------: | ----: |
   | postgres   |     `2Gi` | `4Gi` |
   | service    |    `320m` | `4Gi` |

   With the current setup (2× short and long-running workers), we would need

   | Resource |  Request |     Limit |
   | -------- | -------: | --------: |
   | CPU      |   `460m` |   `3480m` |
   | Memory   | `4484Mi` | `12768Mi` |

   Requesting the memory quotas to be multiplied by 3 results in having ~`11Gi`
   memory left which should be enough to scale up for few more workers if
   needed. This setup would also allow scaling up to 8 workers per each queue.

1. Request adjustments of the quotas such that we can have some buffer (database
   migrations, higher load on service, etc.), but also could **permanently**
   scale up the workers if we find service to be more reliable that way

   - Based on the calculations above, 2× the current quotas on memory would be
     sufficient, but if we were to scale the workers up too (and account for
     possible adjustments, e.g., Redict) we should probably go for 3×

1. Migrate tokman to different toolchain, it's a small self-contained app, so it
   is easy to migrate to either Rust or Go that should leave smaller footprint.

   - Opened an issue for testing out running without Tokman deployment
     https://github.com/packit/tokman/issues/72

   - Opened an issue for migrating in case we need the tokman
     To be opened, if the previous issue “fails” (i.e. tokman is still needed,
     or dropping affects the amount of requests to GitHub in a negative way)

[^1]:
    includes non-scalable deployments, i.e., each runs just one pod, e.g.,
    dashboard, redict, postgres, etc.
