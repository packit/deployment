IMAGE=docker.io/usercont/import-images

# https://github.com/packit/deployment/issues/112#issuecomment-673343049
# CONTAINER_ENGINE ?= $(shell command -v podman 2> /dev/null || echo docker)
CONTAINER_ENGINE ?= docker

image:
	$(CONTAINER_ENGINE) build --rm -t $(IMAGE) .

push:
	$(CONTAINER_ENGINE) push $(IMAGE)

# first: 'oc login', 'oc project packit-${DEPLOYMENT}'
deploy:
	oc create -f job-import-images.yaml
