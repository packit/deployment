#!/usr/bin/bash

oc login "${HOST}" --token="${TOKEN}"

set -x

DEFAULT_NAMESPACE="packit-${DEPLOYMENT}-sandbox"
SANDBOX_NAMESPACE="${SANDBOX_NAMESPACE:-$DEFAULT_NAMESPACE}"

oc get pvc -n "${SANDBOX_NAMESPACE}" |
while IFS= read -r line; do
  age=$(echo "${line}" | awk '{print $7}')
  if [ "${age: -1}" == "d" ]; # days
  then
    name=$(echo "${line}" | awk '{print $1}')
    echo "deleting ${name}"
    oc delete pvc "${name}" -n "${SANDBOX_NAMESPACE}"
  fi
done
