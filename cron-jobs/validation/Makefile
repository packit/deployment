IMAGE=quay.io/packit/packit-service-validation
ANSIBLE_PYTHON := /usr/bin/python3
AP := ansible-playbook -vv -c local -i localhost, -e ansible_python_interpreter=$(ANSIBLE_PYTHON)

CONTAINER_ENGINE ?= $(shell command -v podman 2> /dev/null || echo docker)

image:
	$(CONTAINER_ENGINE) build --rm -t $(IMAGE) .

push:
	$(CONTAINER_ENGINE) push $(IMAGE)

deploy:
	$(AP) deploy-validation.yaml
