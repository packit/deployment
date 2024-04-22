#!/usr/bin/bash

# Mimic what we do during deployment when we render secret files
# from their templates before we create k8s secrets from them.

set -euo pipefail

# Set default values if not set already
: "${SERVICE:=packit}"
: "${DEPLOYMENT:=dev}"

# Where to process the files
DEFAULT_PATH_TO_SECRETS="secrets/${SERVICE}/${DEPLOYMENT}/"
: "${PATH_TO_SECRETS:=$DEFAULT_PATH_TO_SECRETS}"

ansible-playbook -v -c local -i localhost, \
                 -e path_to_secrets="$(realpath "${PATH_TO_SECRETS}")" \
                 -e service="${SERVICE}" \
                 playbooks/render_secrets_from_templates.yml

echo "[WARNING] Please make sure your ‹vars/› are up-to-date, since the rendered secrets may depend on it."
