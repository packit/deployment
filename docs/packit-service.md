## Packit service/bot deployment specifics

### Repository cache

To shorten the cloning time and making it possible to clone big repositories
(like kernel), the service supports caching git repositories.

To make it work, you need to:

- Configure the cache in the service config:

```yaml
# Path of the cache (mounted as a persistent volume in our case)
repository_cache: /repository-cache
# The maintenance of the cache (adding, updating) is done externally,
# not in the packit/packit-service code.
add_repositories_to_repository_cache: false
```

- Since our infrastructure does not support shared volumes, we need to attach
  one volume with a cache to each worker and one to each corresponding sandbox
  pod.
  - In the case of workers, this is done during the deployment.
  - For sandboxes, there is an option in the service config (the environment
    variable needs to differ for each worker and is set during startup of the
    worker):

```yaml
command_handler_pvc_volume_specs:
  - path: /repository-cache
    pvc_from_env: SANDCASTLE_REPOSITORY_CACHE_VOLUME
```

- And finally, add some repositories to the cache.
  - To add a repository, clone/copy the git repository to the
    `/repository-cache` directory. (Each project as a subdirectory.)
  - Be aware, that all the volumes, both the ones used by workers and the ones
    used by sandbox pods, need to have the repository there.
  - For small projects, you can clone the repository from the pod's shell.
  - In the case of larger repositories (like kernel), you can clone the
    repository on your localhost and use `oc rsync` to copy the repository to
    the volume.
  - For the worker's volume, you can `oc rsh` to the worker pod to get to the
    volume.
  - To populate volumes attached to sandbox pods, you can wait for some action
    to be executed or create a new pod (e.g. `oc create -f ./openshift/repository-cache-filler.yml` using and adjusting the name of
    the volume in [this definition](./openshift/repository-cache-filler.yml))
    with the volume attached. This will block the creation of the sandbox pods
    because the volume can't be mounted from multiple pods, so don't forget to
    delete the pod after you finished populating the cache.
