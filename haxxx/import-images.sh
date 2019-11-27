#!/usr/bin/bash

oc login https://api.pro-eu-west-1.openshift.com --token="${TOKEN}" --insecure-skip-tls-verify

set -x

oc import-image is/packit-service:"${DEPLOYMENT}" -n packit-"${DEPLOYMENT}"
oc import-image is/packit-service-fedmsg:"${DEPLOYMENT}" -n packit-"${DEPLOYMENT}"
oc import-image is/packit-worker:"${DEPLOYMENT}" -n packit-"${DEPLOYMENT}"
