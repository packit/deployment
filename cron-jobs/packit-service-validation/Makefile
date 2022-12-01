IMAGE=quay.io/packit/packit-service-validation
CONTAINER_ENGINE ?= $(shell command -v podman 2> /dev/null || echo docker)

image:
	$(CONTAINER_ENGINE) build --rm -t $(IMAGE) .

push:
	$(CONTAINER_ENGINE) push $(IMAGE)
