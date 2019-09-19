.PHONY: send-release-event deploy cleanup zuul-secrets get-certs

CONT_HOME := /opt/app-root/src

# use route when doing this on a remote openshift cluster
send-release-event:
	curl -d "@test_data/release_event.json" -H "Content-Type: application/json" -X POST http://$(shell oc get svc packit-service -o json | jq -r .spec.clusterIP)/webhooks/github/release

deploy:
	ansible-playbook -vv playbooks/deploy.yml

cleanup:
	ansible-playbook -vv playbooks/cleanup.yml

zuul-secrets:
	ansible-playbook -vv playbooks/zuul-secrets.yml

get-certs:
	ansible-playbook -vv playbooks/get-certs.yml
