IMAGE=docker.io/usercont/packit-service-validation
ANSIBLE_PYTHON := /usr/bin/python3
AP := ansible-playbook -vv -c local -i localhost, -e ansible_python_interpreter=$(ANSIBLE_PYTHON)

# https://github.com/packit/deployment/issues/112#issuecomment-673343049
# CONTAINER_ENGINE ?= $(shell command -v podman 2> /dev/null || echo docker)
CONTAINER_ENGINE ?= docker

image:
	$(CONTAINER_ENGINE) build --rm -t $(IMAGE) .

push:
	$(CONTAINER_ENGINE) push $(IMAGE)

deploy:
	$(AP) deploy-validation.yaml
