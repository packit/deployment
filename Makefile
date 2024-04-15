.PHONY: send-release-event deploy tags cleanup zuul-secrets move-stable

ANSIBLE_PYTHON ?= $(shell command -v /usr/bin/python3 2> /dev/null || echo /usr/bin/python2)
CONT_HOME := /opt/app-root/src
AP := ansible-playbook -vv -c local -i localhost, -e ansible_python_interpreter=$(ANSIBLE_PYTHON)
# "By default, Ansible runs as if --tags all had been specified."
# https://docs.ansible.com/ansible/latest/user_guide/playbooks_tags.html#special-tags
TAGS ?= all
VAGRANT_SSH_PORT = "$(shell cd containers && vagrant ssh-config | awk '/Port/{print $$2}')"
VAGRANT_SSH_USER = "$(shell cd containers && vagrant ssh-config | awk '/User/{print $$2}')"
VAGRANT_SSH_GUEST = "$(shell cd containers && vagrant ssh-config | awk '/HostName/{print $$2}')"
VAGRANT_SSH_IDENTITY_FILE = "$(shell cd containers && vagrant ssh-config | awk '/IdentityFile/{print $$2}')"
VAGRANT_SSH_CONFIG = $(shell cd containers && vagrant ssh-config | awk 'NR>1 {print " -o "$$1"="$$2}')
VAGRANT_SHARED_DIR = "/vagrant"

CENTOS_VAGRANT_BOX = CentOS-Stream-Vagrant-8-latest.x86_64.vagrant-libvirt.box
CENTOS_VAGRANT_URL = https://cloud.centos.org/centos/8-stream/x86_64/images/$(CENTOS_VAGRANT_BOX)

ifneq "$(shell whoami)" "root"
	ASK_PASS ?= --ask-become-pass
endif

# Only for Packit team members with access to Bitwarden vault
# if not working prepend OPENSSL_CONF=/dev/null to script invocation
download-secrets:
	./scripts/download_secrets.sh

# Mimic what we do during deployment when we render secret files
# from their templates before we create k8s secrets from them.
render-secrets-from-templates:
	./scripts/render_secrets_from_templates.sh

# If you're sure you want to skip the secrets downloading,
# because for example you just did it and you don't want to wait for it again
# just set SKIP_SECRETS_SYNC or SSS to any value.
deploy: download-secrets
	$(AP) playbooks/deploy.yml --tags $(TAGS)

tags:
	$(AP) playbooks/deploy.yml --list-tags

cleanup:
	$(AP) playbooks/cleanup.yml

# Import newer images from registry.
# Causes re-deployment of components with newer image available.
import-images:
	$(AP) playbooks/import-images.yml

zuul-secrets:
	$(AP) playbooks/zuul-secrets.yml

generate-local-secrets:
	$(AP) $(ASK_PASS) playbooks/generate-local-secrets.yml

# Check whether everything has been deployed OK with 'make deploy'
check:
	$(AP) playbooks/check.yml

move-stable:
	[[ -d move_stable_repositories ]] || scripts/move_stable.py init
	scripts/move_stable.py move-all

oc-cluster-create:
# vagrant pointer is broken...
	[[ -f $(CENTOS_VAGRANT_BOX) ]] || wget $(CENTOS_VAGRANT_URL)
	cd containers && vagrant up

oc-cluster-destroy:
	cd containers && vagrant destroy

oc-cluster-up:
	cd containers && vagrant up
	cd containers && vagrant ssh -c "cd $(VAGRANT_SHARED_DIR) && $(AP) playbooks/oc-cluster-run.yml"

oc-cluster-down:
	cd containers && vagrant halt

oc-cluster-ssh: oc-cluster-up
	ssh $(VAGRANT_SSH_CONFIG) localhost

test-deploy:
# to be run inside VM where the oc cluster is running! Call make tmt-tests instead.
	DEPLOYMENT=dev $(AP) playbooks/generate-local-secrets.yml
	DEPLOYMENT=dev $(AP) -e '{"src_dir": $(VAGRANT_SHARED_DIR)}' playbooks/test_deploy_setup.yml
	DEPLOYMENT=dev $(AP) -e '{"container_engine": "podman", "registry": "default-route-openshift-image-registry.apps-crc.testing", "registry_user": "kubeadmin", "src_dir": $(VAGRANT_SHARED_DIR)}' playbooks/deploy.yml
	DEPLOYMENT=dev $(AP) -e '{"container_engine": "podman", "registry": "default-route-openshift-image-registry.apps-crc.testing", "registry_user": "kubeadmin", "src_dir": $(VAGRANT_SHARED_DIR)}' playbooks/check.yml

tmt-tests:
	tmt run --all provision --how connect --user vagrant --guest $(VAGRANT_SSH_GUEST) --port $(VAGRANT_SSH_PORT) --key $(VAGRANT_SSH_IDENTITY_FILE)
