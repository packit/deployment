.PHONY: send-release-event deploy tags cleanup zuul-secrets get-certs

ANSIBLE_PYTHON := /usr/bin/python3
CONT_HOME := /opt/app-root/src
AP := ansible-playbook -vv -c local -i localhost, -e ansible_python_interpreter=$(ANSIBLE_PYTHON)
# "By default, Ansible runs as if --tags all had been specified."
# https://docs.ansible.com/ansible/latest/user_guide/playbooks_tags.html#special-tags
TAGS ?= all

# use route when doing this on a remote openshift cluster
send-release-event:
	curl -d "@test_data/release_event.json" -H "Content-Type: application/json" -X POST http://$(shell oc get svc packit-service -o json | jq -r .spec.clusterIP)/webhooks/github/release

deploy:
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

get-certs:
	$(AP) playbooks/get-certs.yml

get-certs-dashboard:
	$(AP) -e domain=dashboard.stg.packit.dev playbooks/get-certs.yml

generate-local-secrets:
	$(AP) playbooks/generate-local-secrets.yml

deploy-validation:
	$(AP) cron-jobs/validation/deploy-validation.yaml

# DEPLOYMENT is always stg because this cronjob is not related to specific deployment stage a
# needs be configure only once
deploy-rebuild-base-image:
	DEPLOYMENT=stg $(AP) playbooks/rebuild-base-image.yml
