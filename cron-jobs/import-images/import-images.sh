#!/usr/bin/bash

oc login "${HOST}" --token="${TOKEN}" --insecure-skip-tls-verify

set -ux

: "${SERVICE:=packit}"
: "${NAMESPACE:=${SERVICE}-${DEPLOYMENT}}"

oc import-image is/packit-service:"${DEPLOYMENT}" -n "${NAMESPACE}"
oc import-image is/packit-worker:"${DEPLOYMENT}" -n "${NAMESPACE}"
oc import-image is/fluentd:"${DEPLOYMENT}" -n "${NAMESPACE}"

if [[ "${SERVICE}" == "packit" ]]; then
  oc import-image is/packit-dashboard:"${DEPLOYMENT}" -n "${NAMESPACE}"
  oc import-image is/tokman:"${DEPLOYMENT}" -n "${NAMESPACE}"
fi

if [[ "${SERVICE}" != "stream" ]]; then
  oc import-image is/packit-service-fedmsg:"${DEPLOYMENT}" -n "${NAMESPACE}"
fi
