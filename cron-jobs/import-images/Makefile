IMAGE=quay.io/packit/import-images

CONTAINER_ENGINE ?= $(shell command -v podman 2> /dev/null || echo docker)

image:
	$(CONTAINER_ENGINE) build --rm -t $(IMAGE) .

push:
	$(CONTAINER_ENGINE) push $(IMAGE)
