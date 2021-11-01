#!/usr/bin/bash

oc login "${HOST}" --token="${TOKEN}" --insecure-skip-tls-verify

set -x

DEFAULT_SERVICE="packit"
SERVICE="${SERVICE:-$DEFAULT_SERVICE}"
DEFAULT_NAMESPACE="${SERVICE}-${DEPLOYMENT}"
NAMESPACE="${NAMESPACE:-$DEFAULT_NAMESPACE}"

oc import-image is/packit-service:"${DEPLOYMENT}" -n "${NAMESPACE}"
oc import-image is/packit-worker:"${DEPLOYMENT}" -n "${NAMESPACE}"

if [[ "${SERVICE}" == "packit" ]]; then
  oc import-image is/packit-dashboard:"${DEPLOYMENT}" -n "${NAMESPACE}"
  oc import-image is/packit-service-fedmsg:"${DEPLOYMENT}" -n "${NAMESPACE}"
  oc import-image is/tokman:"${DEPLOYMENT}" -n "${NAMESPACE}"
fi
