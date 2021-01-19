IMAGE=quay.io/packit/delete-pvcs

CONTAINER_ENGINE ?= $(shell command -v podman 2> /dev/null || echo docker)

image:
	$(CONTAINER_ENGINE) build --rm -t $(IMAGE) .

push:
	$(CONTAINER_ENGINE) push $(IMAGE)

# first: 'oc login', 'oc project packit-${DEPLOYMENT}-sandbox'
deploy:
	oc create -f job-delete-pvcs.yaml
