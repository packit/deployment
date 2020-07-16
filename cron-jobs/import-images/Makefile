IMAGE=docker.io/usercont/import-images

CONTAINER_ENGINE ?= $(shell command -v podman 2> /dev/null || echo docker)

image:
	$(CONTAINER_ENGINE) build --rm -t $(IMAGE) .

push:
	$(CONTAINER_ENGINE) push $(IMAGE)

# first: 'oc login', 'oc project packit-${DEPLOYMENT}'
deploy:
	oc create -f job-import-images.yaml
