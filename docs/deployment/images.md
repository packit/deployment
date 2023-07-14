---
title: Images
---

# Images

We build separate images for

- [service / web server](https://quay.io/repository/packit/packit-service) - accepts webhooks and tasks workers
- [workers](https://quay.io/repository/packit/packit-worker) - do the actual work
- [fedora messaging consumer](https://quay.io/repository/packit/packit-service-fedmsg) - listens on Fedora Messaging for events
- [Sandcastle](https://quay.io/repository/packit/sandcastle) - provides a [sandbox](https://github.com/packit/sandcastle) environment for `propose-downstream` & `pull-from-upstream`
- [dashboard](https://quay.io/repository/packit/dashboard) - [Dashboard (links to production deployment)](https://dashboard.packit.dev)
- [tokman](https://quay.io/repository/packit/tokman) - [A token manager for GitHub Applications](https://github.com/packit/tokman)
- [hardly](https://quay.io/repository/packit/hardly) - [worker for source-git bot](https://github.com/packit/hardly)

## Production vs. Staging images

Separate images are built for staging and production deployment.
Staging images are `:stg` tagged and built from `main` branches.
Production images are `:prod` tagged and built from `stable` branches.
To move `stable` branches to a newer “_stable commit_” we use [`scripts/move_stable.py`](../scripts/move_stable.py)

## Image build process

Images are automatically built and pushed to [Quay.io](https://quay.io/organization/packit)
by a GitHub workflow whenever a new commit is pushed to `main` or `stable` branch.

In each repo (which builds images) see

- `Actions` tab
- `.github/workflows/*.yml` for configuration of the Action/workflow

For more details about local builds see [packit-service/CONTRIBUTING.md](https://github.com/packit/packit-service/blob/main/CONTRIBUTING.md#building-images-locally)
