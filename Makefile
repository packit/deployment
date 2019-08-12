.PHONY: send-release-event deploy cleanup

CONT_HOME := /opt/app-root/src

PACKIT_SERVICE_IMAGE := docker.io/usercont/packit-service:master
PACKIT_SERVICE_DEPLOY_IMAGE := packit-service-deploy

# use route when doing this on a remote openshift cluster
send-release-event:
	curl -d "@test_data/release_event.json" -H "Content-Type: application/json" -X POST http://$(shell oc get svc packit-service -o json | jq -r .spec.clusterIP)/webhooks/github/release

deploy:
	ansible-playbook --syntax-check playbooks/deploy.yml && ansible-playbook -vv playbooks/deploy.yml

cleanup:
	ansible-playbook --syntax-check playbooks/cleanup.yml && ansible-playbook -vv -c local -i localhost, playbooks/cleanup.yml
