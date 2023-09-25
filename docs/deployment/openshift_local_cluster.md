---
title: Deploy Packit Service on Openshift Local Cluster
---

# Openshift Local

### Get it

https://console.redhat.com/openshift/create/local

### Install it

```bash
cd ~/Downloads
tar xvf crc-linux-amd64.tar.xz
cp ~/Downloads/crc-linux-*-amd64/crc ~/bin
```

### View credentials

```bash
crc console --credentials
```

This command will print out the commands you can use to login into the cluster:

```
To login as a regular user, run 'oc login -u developer -p developer https://api.crc.testing:6443'.
To login as an admin, run 'oc login -u kubeadmin -p fkjhskjhks https://api.crc.testing:6443'
```

### Setup and start the cluster

```bash
crc setup
crc start
```

### Web console

```bash
crc console url
```

### Tweak memory and disk size setup

The cluster is using 9GiB of memory and 30GiB of disk-size by default. Both need to be increased to run packit-service.

```bash
crc config set memory 11264 MiB
crc config set disk-size 41 Gi
```

if the cluster is already running then

```bash
crc stop
crc start
```

# Use Openshift Local internal registry

## Verify a route to the registry exist

```bash
oc get route -n openshift-image-registry
```

## Access the registry using port forwarding

```bash
oc port-forward pod/$(oc get pods -n openshift-image-registry | awk '/^image-registry/{print $1}') -n openshift-image-registry 5000 &
export REGISTRY_SERVICE="localhost:5000/myproject"
podman login --tls-verify=false -u unused -p $(oc whoami -t)  ${REGISTRY_SERVICE}
export REGISTRY_SANDBOX="localhost:5000/packit-dev-sandbox"
podman login --tls-verify=false -u unused -p $(oc whoami -t)  ${REGISTRY_SANDBOX}
```

## Push local images to the registry

```
podman push 3c0d620f8caf ${REGISTRY_SERVICE}/packit-service:dev
podman push 4a087c98c604 ${REGISTRY_SERVICE}/packit-worker:dev
podman push ab2209c59df0 ${REGISTRY_SANDBOX}/sandcastle:dev
```

To be able to successfully deploy images, `myproject` and `packit-dev-sandbox` projects have to exist in the cluster.

# Deploy packit-service

Be sure to login with the same token you have in your deployment configuration

```
cd where-this-repo-is
oc login --token=taken-from-webapp --server=https://api.crc.testing:6443
DEPLOYMENT=dev make deploy
```

## How to patch and configure the projects (just an example)

### Deployment project patches

```diff
diff --git a/playbooks/deploy.yml b/playbooks/deploy.yml
index feb7ef6..442a5c8 100644
--- a/playbooks/deploy.yml
+++ b/playbooks/deploy.yml
@@ -22,12 +22,16 @@
     push_dev_images: false
     with_fluentd_sidecar: false
     postgres_version: 13
-    image: quay.io/packit/packit-service:{{ deployment }}
-    image_worker: quay.io/packit/packit-worker:{{ deployment }}
-    image_fedmsg: quay.io/packit/packit-service-fedmsg:{{ deployment }}
-    image_dashboard: quay.io/packit/dashboard:{{ deployment }}
-    image_tokman: quay.io/packit/tokman:{{ deployment }}
-    image_fluentd: quay.io/packit/fluentd-splunk-hec:latest
+    # registry: quay.io
+    registry: image-registry.openshift-image-registry.svc:5000
+    # registry_project: packit
+    registry_project: myproject
+    image: "{{ registry }}/{{ registry_project }}/packit-service:{{ deployment }}"
+    image_worker: "{{ registry }}/{{ registry_project }}/packit-worker:{{ deployment }}"
+    image_fedmsg: "{{ registry }}/{{ registry_project }}/packit-service-fedmsg:{{ deployment }}"
+    image_dashboard: "{{ registry }}/{{ registry_project }}/dashboard:{{ deployment }}"
+    image_tokman: "{{ registry }}/{{ registry_project }}/tokman:{{ deployment }}"
+    image_fluentd: "{{ registry }}/{{ registry_project }}/fluentd:{{ deployment }}"
     # project_dir is set in tasks/project-dir.yml
     path_to_secrets: "{{ project_dir }}/secrets/{{ service }}/{{ deployment }}"
     # to be used in Image streams as importPolicy:scheduled value
@@ -35,7 +39,7 @@
     # used in dev/zuul deployment to tag & push images to cluster
     # https://github.com/packit/deployment/issues/112#issuecomment-673343049
     # container_engine: "{{ lookup('pipe', 'command -v podman 2> /dev/null || echo docker') }}"
-    container_engine: docker
+    container_engine: podman
     celery_app: packit_service.worker.tasks
     celery_retry_limit: 2
     celery_retry_backoff: 3
diff --git a/playbooks/import-images.yml b/playbooks/import-images.yml
index 959bc78..7c0be12 100644
--- a/playbooks/import-images.yml
+++ b/playbooks/import-images.yml
@@ -10,7 +10,7 @@
     with_fedmsg: true
     with_dashboard: true
     with_tokman: true
-    with_fluentd_sidecar: true
+    with_fluentd_sidecar: false
   tasks:
     - name: Include variables
       ansible.builtin.include_vars: ../vars/{{ service }}/{{ deployment }}.yml
```

### Deployment configuration file: vars/packit/dev.yaml

```yaml
# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

# -------------------------------------------------------------------
# Variables needed by Ansible playbooks in playbooks/
# -------------------------------------------------------------------

# Openshift project/namespace name
project: myproject

# Openshift cluster url
host: https://api.crc.testing:6443

# oc login <the above host value>, oc whoami -t
# OR via Openshift web GUI: click on your login in top right corner, 'Copy Login Command', take the part after --token=
api_key: ""
validate_certs: false
check_up_to_date: false
push_dev_images: false # pushing dev images manually!

# Check that the deployment resources are up-to-date
# check_up_to_date: true

# Check that the current vars file us up to date with the template
# check_vars_template_diff: true

with_tokman: false

# if you want to deploy fedmsg, please make sure to
# edit the queue name in secrets/*/fedora.toml
with_fedmsg: false

with_redis_commander: false

with_flower: false

with_beat: false

with_dashboard: false

with_pushgateway: false

with_fluentd_sidecar: false

managed_platform: false

# with_repository_cache: true
# repository_cache_storage: 4Gi

# image to use for service
# image: quay.io/packit/packit-service:{{ deployment }}

# image to use for worker
# image_worker: quay.io/packit/packit-worker:{{ deployment }}

# image to use for fedora messaging consumer
# image_fedmsg: quay.io/packit/packit-service-fedmsg:{{ deployment }}

# image to use for dashboard
# image_dashboard: "quay.io/packit/dashboard:{{ deployment }}"

# image to use for tokman
# image_tokman: "quay.io/packit/tokman:{{ deployment }}"

# image to use for fluentd sidecar
# image_fluentd: quay.io/packit/fluentd-splunk-hec:latest

# Path to secrets (in case you don't have it in the root of this project)
# path_to_secrets: ../secrets

# Used in dev/Zuul deployment to tag & push images to cluster.
# It's set to "/usr/bin/podman" if there's podman installed, or to 'docker' otherwise.
# If you still want to use docker even when podman is installed, set:
# container_engine: docker

# postgres_version: 15 # MP+

# Celery retry parameters
# celery_retry_limit: 2
# celery_retry_backoff: 3

# Number of worker pods to be deployed to serve the queues
workers_all_tasks: 1
workers_short_running: 0
workers_long_running: 0
# pushgateway_address: http://pushgateway
```

### Deployment configuration file: secrets/packit/dev/packit-service.yaml.j2

```
--
deployment: stg
debug: true
fas_user: packit-stg
keytab_path: /secrets/fedora.keytab
comment_command_prefix: "/packit-stg"
validate_webhooks: true

{{ vault.packit_service | to_nice_yaml }}

testing_farm_api_url: https://api.dev.testing-farm.io/v0.1/
enabled_projects_for_internal_tf:
  - github.com/packit/hello-world

command_handler: sandcastle
command_handler_work_dir: /tmp/sandcastle
command_handler_image_reference: image-registry.openshift-image-registry.svc:5000/packit-dev-sandbox/sandcastle:dev
command_handler_k8s_namespace: {{ sandbox_namespace }}
command_handler_pvc_volume_specs:
  - path: /repository-cache
    pvc_from_env: SANDCASTLE_REPOSITORY_CACHE_VOLUME
    read_only: true
command_handler_storage_class: crc-csi-hostpath-provisioner

repository_cache: /repository-cache
# The maintenance of the cache (adding, updating) is done externally,
# not in the packit/packit-service code.
add_repositories_to_repository_cache: false

appcode: PCKT-002

admins:  # GitHub usernames
  - jpopelka
  - lachmanfrantisek
  - lbarcziova
  - TomasTomecek
  - thrix  # Miro Vadkerti
  - psss  # Petr Splichal
  - csomh
  - mfocko
  - majamassarini
  - nforro

enabled_private_namespaces:
  - gitlab.com/redhat/centos-stream
  - gitlab.com/redhat/centos-stream/src

enabled_projects_for_srpm_in_copr:
  - github.com/packit/hello-world

server_name: stg.packit.dev
dashboard_url: https://dashboard.stg.packit.dev

projects_to_sync:
  - forge: https://github.com
    repo_namespace: packit
    repo_name: packit
    branch: main
    dg_branch: rawhide
    dg_repo_name: packit

  - forge: https://github.com
    repo_namespace: packit
    repo_name: ogr
    branch: main
    dg_branch: rawhide
    dg_repo_name: python-ogr

  - forge: https://github.com
    repo_namespace: packit
    repo_name: requre
    branch: main
    dg_branch: rawhide
    dg_repo_name: python-requre
```

### packit-service project patches

One way for building a debuggable `packit-service:dev` image is running `podman-compose`.

```
podman-compose build --no-cache
```

after applying this patches (and customizing the `celerizer.py` message as you want):

```diff
diff --git a/docker-compose.yml b/docker-compose.yml
index d1a592dc..8ef9675f 100644
--- a/docker-compose.yml
+++ b/docker-compose.yml
@@ -81,11 +81,14 @@ services:
       - tokman
       - redis
       - postgres
+    ports:
+      - 5678:5678
     environment:
       DEPLOYMENT: dev
+      PACKIT_HOME: /home/packit
       REDIS_SERVICE_HOST: redis
       APP: packit_service.worker.tasks
-      KRB5CCNAME: FILE:/tmp/krb5cc_packit
+      KRB5CCNAME: "DIR:/home/packit/kerberos/"
       POSTGRESQL_USER: packit
       POSTGRESQL_PASSWORD: secret-password
       POSTGRESQL_HOST: postgres
diff --git a/files/docker/Dockerfile b/files/docker/Dockerfile
index f2a82282..19013b98 100644
--- a/files/docker/Dockerfile
+++ b/files/docker/Dockerfile
@@ -32,6 +32,9 @@ RUN git rev-parse HEAD >/.packit-service.git.commit.hash \
 COPY alembic.ini ./
 COPY alembic/ ./alembic/

+# Allow remote debugging
+RUN pip install --upgrade debugpy
+
 EXPOSE 8443

 CMD ["/usr/bin/run_httpd.sh"]
diff --git a/files/docker/Dockerfile.worker b/files/docker/Dockerfile.worker
index aa06755e..a292ef52 100644
--- a/files/docker/Dockerfile.worker
+++ b/files/docker/Dockerfile.worker
@@ -15,6 +15,9 @@ ENV USER=packit \
 # Ansible doesn't like /tmp
 WORKDIR /src

+# Allow remote debugging
+RUN pip install --upgrade debugpy
+
 COPY files/install-deps-worker.yaml ./files/
 COPY files/tasks/ ./files/tasks/
 RUN ansible-playbook -vv -c local -i localhost, files/install-deps-worker.yaml \
diff --git a/files/install-deps-worker.yaml b/files/install-deps-worker.yaml
index c348944e..97727a49 100644
--- a/files/install-deps-worker.yaml
+++ b/files/install-deps-worker.yaml
@@ -46,7 +46,7 @@
     - name: Install pip deps
       ansible.builtin.pip:
         name:
-          - git+https://github.com/packit/sandcastle.git@{{ source_branch }}
+          - git+https://github.com/majamassarini/sandcastle.git@static-execute-dir-name
           # The above bodhi-client RPM installs python3-requests-2.25.1 and python3-urllib3-1.26.5
           # The below sentry_sdk would then install urllib3-2.x because of its urllib3>=1.26.11 requirement
           # and 'pip check' would then scream that "requests 2.25.1 has requirement urllib3<1.27"
diff --git a/packit_service/celerizer.py b/packit_service/celerizer.py
index e9279919..1e0b9710 100644
--- a/packit_service/celerizer.py
+++ b/packit_service/celerizer.py
@@ -42,4 +42,176 @@ def get_celery_application():
     return app


+# Let a remote debugger (Visual Studio Code client)
+# access this running instance.
+import debugpy
+
+# Allow other computers to attach to debugpy at this IP address and port.
+try:
+    debugpy.listen(("0.0.0.0", 5678))
+
+    # Uncomment the following lines if you want to
+    # pause the program until a remote debugger is attached
+
+    # print("Waiting for debugger attach")
+    debugpy.wait_for_client()
+
+except RuntimeError as e:
+    pass
+
+
+
+import json
+
+comment_copr_build_event = """
+{
+  "agent": "mmassari",
+  "pullrequest": {
+    "assignee": null,
+    "branch": "rawhide",
+    "branch_from": "custumized-packit-action",
+    "cached_merge_status": "FFORWARD",
+    "closed_at": null,
+    "closed_by": null,
+    "comments": [
+      {
+        "comment": "/packit-stg pull-from-upstream --with-pr-config",
+        "commit": null,
+        "date_created": "1693297834",
+        "edited_on": null,
+        "editor": null,
+        "filename": null,
+        "id": 155947,
+        "line": null,
+        "notification": false,
+        "parent": null,
+        "reactions": {},
+        "tree": null,
+        "user": {
+          "full_url": "https://src.fedoraproject.org/user/mmassari",
+          "fullname": "Maja Massarini",
+          "name": "mmassari",
+          "url_path": "user/mmassari"
+        }
+      }
+    ],
+    "commit_start": "62df8b5ad073d4b299620e7aa81aaafeaee71bb9",
+    "commit_stop": "62df8b5ad073d4b299620e7aa81aaafeaee71bb9",
+    "date_created": "1693297764",
+    "full_url": "https://src.fedoraproject.org/rpms/python-teamcity-messages/pull-request/45",
+    "id": 45,
+    "initial_comment": null,
+    "last_updated": "1693297834",
+    "project": {
+      "access_groups": {
+        "admin": [],
+        "collaborator": [],
+        "commit": [],
+        "ticket": []
+      },
+      "access_users": {
+        "admin": [
+          "limb"
+        ],
+        "collaborator": [],
+        "commit": [],
+        "owner": [
+          "mmassari"
+        ],
+        "ticket": []
+      },
+      "close_status": [],
+      "custom_keys": [],
+      "date_created": "1643654065",
+      "date_modified": "1675768016",
+      "description": "The python-teamcity-messages package",
+      "full_url": "https://src.fedoraproject.org/rpms/python-teamcity-messages",
+      "fullname": "rpms/python-teamcity-messages",
+      "id": 54766,
+      "milestones": {},
+      "name": "python-teamcity-messages",
+      "namespace": "rpms",
+      "parent": null,
+      "priorities": {},
+      "tags": [],
+      "url_path": "rpms/python-teamcity-messages",
+      "user": {
+        "full_url": "https://src.fedoraproject.org/user/mmassari",
+        "fullname": "Maja Massarini",
+        "name": "mmassari",
+        "url_path": "user/mmassari"
+      }
+    },
+    "remote_git": null,
+    "repo_from": {
+      "access_groups": {
+        "admin": [],
+        "collaborator": [],
+        "commit": [],
+        "ticket": []
+      },
+      "access_users": {
+        "admin": [
+          "limb"
+        ],
+        "collaborator": [],
+        "commit": [],
+        "owner": [
+          "mmassari"
+        ],
+        "ticket": []
+      },
+      "close_status": [],
+      "custom_keys": [],
+      "date_created": "1643654065",
+      "date_modified": "1675768016",
+      "description": "The python-teamcity-messages package",
+      "full_url": "https://src.fedoraproject.org/rpms/python-teamcity-messages",
+      "fullname": "rpms/python-teamcity-messages",
+      "id": 54766,
+      "milestones": {},
+      "name": "python-teamcity-messages",
+      "namespace": "rpms",
+      "parent": null,
+      "priorities": {},
+      "tags": [],
+      "url_path": "rpms/python-teamcity-messages",
+      "user": {
+        "full_url": "https://src.fedoraproject.org/user/mmassari",
+        "fullname": "Maja Massarini",
+        "name": "mmassari",
+        "url_path": "user/mmassari"
+      }
+    },
+    "status": "Open",
+    "tags": [],
+    "threshold_reached": null,
+    "title": "Add actions for testing purpose",
+    "uid": "139c2b91041b4e939384283169f389d6",
+    "updated_on": "1693297834",
+    "user": {
+      "full_url": "https://src.fedoraproject.org/user/mmassari",
+      "fullname": "Maja Massarini",
+      "name": "mmassari",
+      "url_path": "user/mmassari"
+    }
+  },
+  "headers": {
+    "fedora_messaging_schema": "pagure.pull-request.comment.added",
+    "fedora_messaging_severity": 20,
+    "fedora_messaging_user_mmassari": true,
+    "sent-at": "2023-08-29T08:30:35+00:00"
+  },
+  "topic": "org.fedoraproject.prod.pagure.pull-request.comment.added"
+}
+"""
+
+event = json.loads(comment_copr_build_event)
 celery_app: Celery = Proxy(get_celery_application)
+celery_app.send_task(
+    name="task.steve_jobs.process_message",
+    kwargs={"event": event},
+)
+
+
diff --git a/packit_service/constants.py b/packit_service/constants.py
index f5b3e1aa..21707465 100644
--- a/packit_service/constants.py
+++ b/packit_service/constants.py
@@ -18,7 +18,8 @@ DOCS_TESTING_FARM = f"{DOCS_URL}/testing-farm"
 KOJI_PRODUCTION_BUILDS_ISSUE = "https://pagure.io/releng/issue/9801"

 SANDCASTLE_WORK_DIR = "/tmp/sandcastle"
-SANDCASTLE_IMAGE = "quay.io/packit/sandcastle"
+#SANDCASTLE_IMAGE = "quay.io/packit/sandcastle"
+SANDCASTLE_IMAGE = "image-registry.openshift-image-registry.svc:5000/packit-dev-sandbox/sandcastle"
 SANDCASTLE_DEFAULT_PROJECT = "myproject"
 SANDCASTLE_PVC = "SANDCASTLE_PVC"

diff --git a/packit_service/worker/monitoring.py b/packit_service/worker/monitoring.py
index 05ce236c..26f189c3 100644
--- a/packit_service/worker/monitoring.py
+++ b/packit_service/worker/monitoring.py
@@ -165,6 +165,8 @@ class Pushgateway:
             return

         logger.info("Pushing the metrics to pushgateway.")
-        push_to_gateway(
-            self.pushgateway_address, job=self.worker_name, registry=self.registry
-        )
+        try:
+            push_to_gateway(
+                self.pushgateway_address, job=self.worker_name, registry=self.registry
+            )
+        except: pass # gaierror in Openshift Local
```

## Debug the worker with port forwarding

```
oc port-forward pod/$(oc get pods -n myproject | awk '/^packit-worker/{print $1}') -n myproject 5678
```

If you use the microsoft `debugpy` for debugging probably you need something similar to the following in a file named `.vscode/launch.json` for Visual Studio Code to attach the breakpoint

```
        {
            "name": "Python: Remote Attach packit code remotely",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "localhost",
                "port": 5678
            },
            "justMyCode": false,
            "pathMappings": [
                {
                    "localRoot": "/your-packit-source-dir/packit",
                    "remoteRoot": "/usr/local/lib/python3.9/site-packages"
                },
            ]
        },
```

## Debug sandcastle

### Create sandcastle volumes manually

#### Create PersistentVolume1

```
apiVersion: v1
kind: PersistentVolume
metadata:
  name: sandcastle-volume-1
  namespace: packit-dev-sandbox
  labels:
    type: local
spec:
  claimRef:
    name: sandcastle-repository-cache-packit-worker-0
    namespace: packit-dev-sandbox
  storageClassName: crc-csi-hostpath-provisioner
  accessModes:
    - ReadWriteOnce
  capacity:
    storage: 4Gi
  hostPath:
    path: "/tmp/sandbox1"
  volumeMode: Filesystem
  persistentVolumeReclaimPolicy: Recycle
```

#### Create PersistentVolume2 (and manually adjust the claimRef name once the sandcastle pod is running...)

```
apiVersion: v1
kind: PersistentVolume
metadata:
  name: sandcastle-volume-2
  namespace: packit-dev-sandbox
  labels:
    type: local
spec:
  claimRef:
    name: sandcastle--tmp-sandcastle-20230913-075642340270-pvc
    namespace: packit-dev-sandbox
  storageClassName: crc-csi-hostpath-provisioner
  accessModes:
    - ReadWriteOnce
  capacity:
    storage: 3Gi
  hostPath:
    path: "/tmp/sandbox2"
  volumeMode: Filesystem
  persistentVolumeReclaimPolicy: Recycle
```
