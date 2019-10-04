.PHONY: send-release-event deploy cleanup zuul-secrets get-certs

CONT_HOME := /opt/app-root/src
AP := ansible-playbook -vv -c local -i localhost,

# use route when doing this on a remote openshift cluster
send-release-event:
	curl -d "@test_data/release_event.json" -H "Content-Type: application/json" -X POST http://$(shell oc get svc packit-service -o json | jq -r .spec.clusterIP)/webhooks/github/release

deploy:
	$(AP) playbooks/deploy.yml

cleanup:
	$(AP) playbooks/cleanup.yml

zuul-secrets:
	$(AP) playbooks/zuul-secrets.yml

get-certs:
	$(AP) playbooks/get-certs.yml
