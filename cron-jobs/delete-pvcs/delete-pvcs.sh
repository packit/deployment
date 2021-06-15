#!/usr/bin/bash

oc login "${HOST}" --token="${TOKEN}"

set -x

DEFAULT_NAMESPACE="packit-${DEPLOYMENT}-sandbox"
NAMESPACE="${SANDBOX_NAMESPACE:-$DEFAULT_NAMESPACE}"
POD_NAME_STARTSWITH="quay-io-packit-sandcastle-${DEPLOYMENT}-"

# get all pods with name starting with POD_NAME_STARTSWITH
oc get pod -n "${NAMESPACE}" | grep "^${POD_NAME_STARTSWITH}" |
# for each pod
while IFS= read -r line; do
  pod_status=$(echo "${line}" | awk '{print $3}')
  if [[ "${pod_status}" == "Completed" || "${pod_status}" == "OOMKilled" ]];
  then
    pod_name=$(echo "${line}" | awk '{print $1}')
    pod_age=$(echo "${line}" | awk '{print $5}')

    # get associated PVC name
    pvc_name=$(oc get pod "${pod_name}" -n "${NAMESPACE}" -o=jsonpath="{.spec.volumes[0].persistentVolumeClaim.claimName}")
    echo "Deleting pvc ${pvc_name}"
    oc delete pvc "${pvc_name}" -n "${NAMESPACE}"

    if [[ "${pod_age: -1}" == "d" ]]; # days
    then
      echo "Deleting pod ${pod_name}"
      oc delete pod "${pod_name}" -n "${NAMESPACE}"
    fi
  fi
done
