#!/usr/bin/bash

# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

set -eu

# Set TEST=yes to run the script with a mocked oc.
# See test.sh for test outputs.
TEST="${TEST:-}"

myoc() {
    oc -n "${NAMESPACE}" "$@"
}

if [[ -n "${TEST}" ]]; then
    source "$(dirname $0)/test.sh"
fi

DEFAULT_NAMESPACE="packit-${DEPLOYMENT}-sandbox"
NAMESPACE="${SANDBOX_NAMESPACE:-$DEFAULT_NAMESPACE}"
POD_NAME_PREFIX="quay-io-packit-sandcastle-${DEPLOYMENT}-"
PVC_NAME_PREFIX="sandcastle--sandcastle"
JSONPATH="{.spec.volumes[:].persistentVolumeClaim.claimName}"

myoc login "${HOST}" --token="${TOKEN}"

# ============================================================================
# Delete Completed and OOMKilled sandbox pods older than a day.
# ============================================================================
echo "Checking pods..."
mounted_pvcs=""
while IFS= read -r line; do
    [[ -z "${line}" ]] && continue
    pod_name=$(echo "${line}" | awk '{print $1}')
    pod_status=$(echo "${line}" | awk '{print $3}')
    pod_age=$(echo "${line}" | awk '{print $5}')

    if [[ "${pod_status}" == "Completed" || "${pod_status}" == "OOMKilled" ]] \
        && [[ "${pod_age: -1}" == "d" ]]; # days
    then
        echo "Deleting pod ${pod_name}"
        myoc delete --ignore-not-found pod "${pod_name}"
    else
        # Get associated PVC name.
        # Multiple values are separated by space.
        mounted_pvcs="${mounted_pvcs} $(myoc get pod "${pod_name}" -o=jsonpath=${JSONPATH})"
    fi
done <<<$(myoc get pod | grep "^${POD_NAME_PREFIX}")
# Use awk to filter out empty lines. Grep would exit non-zero if mounted_pvcs is empty.
mounted_pvcs=$(echo "${mounted_pvcs}" | tr ' ' '\n' | awk '/./ {print $0}')

# ============================================================================
# Delete the sandbox PVCs which are not mounted in any pod.
# ============================================================================
echo "Checking PVCs..."
all_pvcs=$(myoc get pvc | awk '$0 !~ "NAME" {print $1}')
while IFS= read -r pvc; do
    [[ -z "${pvc}" ]] && continue
    echo "Deleting pvc ${pvc}"
    myoc delete --ignore-not-found pvc "${pvc}"
done <<<$(echo -e "${mounted_pvcs}\n${all_pvcs}" | grep "^${PVC_NAME_PREFIX}" | sort | uniq -u)
