### Images

We build separate images for

- [service / web server](https://quay.io/repository/packit/packit-service) - accepts webhooks and tasks workers
- [workers](https://quay.io/repository/packit/packit-worker) - do the actual work
- [fedora messaging consumer](https://quay.io/repository/packit/packit-service-fedmsg) - listens on fedora messaging for events from Copr and tasks workers
- [Sandcastle](https://quay.io/repository/packit/sandcastle) - sandboxing

#### Production vs. Staging images

Separate images are built for staging and production deployment.
Staging images are `:stg` tagged and built from `main` of `packit-service`, `packit-service-fedmsg`, `sandcastle` and `dashboard`.
Production images are `:prod` tagged and built from `stable` branch of `packit-service`, `packit-service-fedmsg`, `sandcastle` and `dashboard`.
To move `stable` branches to a newer 'stable' commit we use [scripts/move_stable.py](scripts/move_stable.py)

#### Image build process

Images are automatically built and pushed to [Quay.io](https://quay.io/organization/packit)
by a Github workflow whenever a new commit is pushed to `main` or `stable` branch.

In each repo (which builds images) see

- `Actions` tab
- .github/workflows/\*.yml for configuration of the Action/workflow

For more details about local builds see [packit-service/CONTRIBUTING.md](https://github.com/packit/packit-service/blob/main/CONTRIBUTING.md#building-images-locally)
