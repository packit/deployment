#!/usr/bin/bash

oc login "${HOST}" --token="${TOKEN}"

set -x

NAMESPACE="packit-${DEPLOYMENT}-sandbox"

oc get pvc -n "${NAMESPACE}" |
while IFS= read -r line; do
  age=$(echo "${line}" | awk '{print $7}')
  if [ "${age: -1}" == "d" ]; # days
  then
    name=$(echo "${line}" | awk '{print $1}')
    echo "deleting ${name}"
    oc delete pvc "${name}" -n "${NAMESPACE}"
  fi
done
