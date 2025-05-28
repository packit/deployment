#!/bin/bash

# This quick script updates a data field of an OpenShift secret with the
# content of a file.
#
# The name of the data field is the basename of the file.
#
# Run as:
#
#     scripts/update_oc_secret.sh <secret_name> <path_to_file>
#
# For example:
#
#     scripts/update_oc_secret.sh packit-config secrets/packit/stg/packit-service.yaml
#
# It's up to you to log in to the right cluster and select the right namespace
# to work on.

set -euo pipefail

DATA=$(basename "$2")
oc get secrets/"$1" -o json | jq -r ".data.\"${DATA}\"=$(base64 -w0 < "$2" | jq -sR)" | oc apply -f -
