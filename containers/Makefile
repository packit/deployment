ANSIBLE_PYTHON ?= $(shell command -v /usr/bin/python3 2> /dev/null || echo /usr/bin/python2)
AP := ansible-playbook -vv -c local -i localhost, -e ansible_python_interpreter=$(ANSIBLE_PYTHON)
VAGRANT_SSH_PORT = "$(shell vagrant ssh-config | awk '/Port/{print $$2}')"
VAGRANT_SSH_USER = "$(shell vagrant ssh-config | awk '/User/{print $$2}')"
VAGRANT_SSH_GUEST = "$(shell vagrant ssh-config | awk '/HostName/{print $$2}')"
VAGRANT_SSH_IDENTITY_FILE = "$(shell vagrant ssh-config | awk '/IdentityFile/{print $$2}')"
VAGRANT_SSH_CONFIG = $(shell vagrant ssh-config | awk 'NR>1 {print " -o "$$1"="$$2}')
VAGRANT_SHARED_DIR = "/vagrant"

# to be used when the vagrant box link is broken, should be kept in sync with the Vagrant file
#CENTOS_VAGRANT_BOX = CentOS-Stream-Vagrant-8-latest.x86_64.vagrant-libvirt.box
#CENTOS_VAGRANT_URL = https://cloud.centos.org/centos/8-stream/x86_64/images/$(CENTOS_VAGRANT_BOX)

CRC_PULL_SECRET ?= "$(shell cat secrets/openshift-local-pull-secret.yml)"

# for this command to work, you may need to:
#   sudo systemctl enable --now libvirtd
#   sudo systemctl enable --now virtnetworkd
oc-cluster-create:
	if [ ! -z "$(CENTOS_VAGRANT_BOX)" ] && [ -f $(CENTOS_VAGRANT_BOX) ]; then wget $(CENTOS_VAGRANT_URL); fi;
	vagrant up

oc-cluster-destroy:
	vagrant destroy

oc-cluster-up:
	vagrant up
	vagrant ssh -c "cd $(VAGRANT_SHARED_DIR) && $(AP) --extra-vars user=vagrant playbooks/oc-cluster-run.yml"

oc-cluster-down:
	vagrant halt

oc-cluster-ssh: oc-cluster-up
	ssh $(VAGRANT_SSH_CONFIG) localhost

# Openshift Local pull_secret must exist locally
# or you can also define the CRC_PULL_SECRET var
check-pull-secret:
	if [ ! -f ../secrets/openshift-local-pull-secret.yml ] && [ ! -n "$(CRC_PULL_SECRET)" ]; then echo "no pull secret available create secrets/openshift-local-pull-secret.yml file or set CRC_PULL_SECRET variable"; exit 1; else echo "pull secret found"; fi

# Execute tmt deployment test on a vagrant virtual machine
# The virtual machine has to be already up and running,
# use the target oc-cluster-up
tmt-vagrant-test: check-pull-secret
	tmt run --all provision --how connect --user vagrant --guest $(VAGRANT_SSH_GUEST) --port $(VAGRANT_SSH_PORT) --key $(VAGRANT_SSH_IDENTITY_FILE) plan --name deployment/vagrant
