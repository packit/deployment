#!/usr/bin/bash

# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

# This redefines myoc() to be more like a mock for the real
# commands, and return some output resembling the real one.

HOST=example.com
TOKEN=very-secret-token
DEPLOYMENT=test

# Using this myoc should result in the script deleting
# - 2 pods, and
# - 2 PVCs
myoc() {
    if [[ "$1" == "login" || "$1" == "delete" ]]; then
        echo "oc $@"
    elif [[ "$1 $2" == "get pod" && $# -eq 2 ]]; then
        cat << EOF
NAME                                                   READY     STATUS      RESTARTS   AGE
delete-pvcs-1628060400-qv4mn                           0/1       Completed   0          31m
quay-io-packit-sandcastle-${DEPLOYMENT}-del1           0/1       OOMKilled   1          1d
quay-io-packit-sandcastle-${DEPLOYMENT}-del2           0/1       Completed   0          13d
quay-io-packit-sandcastle-${DEPLOYMENT}-keep1          0/1       Completed   0          12h
quay-io-packit-sandcastle-${DEPLOYMENT}-keep2          1/1       Running     0          7m
EOF
    elif [[ "$1 $2" == "get pod" && $# -gt 2 ]]; then
        case "$3" in
            # PVCs which show up as mounted but then don't show up in the list of PVCs are
            # deleted.
            *-keep1)    echo -n "sandcastle-repository-cache sandcastle--sandcastle-pvc-del1";;
            *-keep2)    echo -n "sandcastle--sandcastle-pvc-keep2 sandcastle-repository-cache";;
            *)          echo "$3 is not a known scenario"; exit 20;;
        esac
    elif [[ "$1 $2" == "get pvc" ]]; then
        cat << EOF
NAME                              STATUS    VOLUME                                     CAPACITY   ACCESS MODES   STORAGECLASS    AGE
sandcastle-repository-cache       Bound     pvc-038e1c39-f35b-11eb-b815-068b91999b6e   16Gi       RWO            gp2-encrypted   2d
some-other-pvc-to-keep            Bound     pvc-038e1c39-f35b-11eb-b815-068b91999b6e   16Gi       RWO            gp2-encrypted   2d
sandcastle--sandcastle-pvc-keep2  Bound     pvc-038e1c38-f35b-11eb-b815-068b91999b6e    2Gi       RWO            gp2-encrypted   2d
sandcastle--sandcastle-pvc-del2   Bound     pvc-038e1c38-f35b-11eb-b815-068b91999b6e    2Gi       RWO            gp2-encrypted   2d
EOF
    else
        echo "No such oc call in the script: $@"
        exit 21
    fi
}
