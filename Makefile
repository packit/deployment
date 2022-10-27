.PHONY: send-release-event deploy tags cleanup zuul-secrets move-stable

ANSIBLE_PYTHON ?= $(shell command -v /usr/bin/python3 2> /dev/null || echo /usr/bin/python2)
CONT_HOME := /opt/app-root/src
AP := ansible-playbook -vv -c local -i localhost, -e ansible_python_interpreter=$(ANSIBLE_PYTHON)
# "By default, Ansible runs as if --tags all had been specified."
# https://docs.ansible.com/ansible/latest/user_guide/playbooks_tags.html#special-tags
TAGS ?= all

download-secrets:
	# Disable the system configuration for OpenSSL, so that older,
	# deprecated algorithms can be used by Bitwarden CLI.
	# TODO: Remove this, once the issue below is resolved.
	# https://github.com/bitwarden/clients/issues/2726#issuecomment-1292153245
	OPENSSL_CONF= ./scripts/download_secrets.sh

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
	$(AP) playbooks/generate-local-secrets.yml

# Check whether everything has been deployed OK with 'make deploy'
check:
	$(AP) playbooks/check.yml

move-stable:
	[[ -d move_stable_repositories ]] || scripts/move_stable.py init
	scripts/move_stable.py move-all
