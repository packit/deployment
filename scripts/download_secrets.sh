#!/usr/bin/bash

# Script to
# - login to Bitwarden and/or unlock the vault
# - download all files attached to secrets-${SERVICE}-${DEPLOYMENT} note
#   into secrets/${SERVICE}/${DEPLOYMENT}/
# Example usage:
# SERVICE=packit DEPLOYMENT=stg PATH_TO_SECRETS=/tmp/xyz/ ./scripts/download_secrets.sh

# If you're about to run this script more times,
# you better run 'bw login || bw unlock' yourself and export the returned BW_SESSION
# so that this script doesn't ask you for the master password every time.
# For example I (jpopelka) have this in my ~/.bashrc
# alias bwunlock='bw unlock --check || export BW_SESSION="$(bw unlock --raw)"'

# Debug
#set -x

# Where to download the files
DEFAULT_PATH_TO_SECRETS="secrets/${SERVICE}/${DEPLOYMENT}/"

# Set default values if not set already
: "${SERVICE:=packit}"
: "${DEPLOYMENT:=dev}"
[[ "${DEPLOYMENT}" == "dev" ]] && { echo "Not downloading secrets for DEPLOYMENT==dev"; exit 0; }
: "${PATH_TO_SECRETS:=$DEFAULT_PATH_TO_SECRETS}"

# Name of the shared (Bitwarden vault) secure note,
# which contains the secret files as attachments.
BW_ITEM="secrets-${SERVICE}-${DEPLOYMENT}"

command -v bw >/dev/null 2>&1 || { echo >&2 "'bw' command not found, see https://bitwarden.com/help/cli"; exit 1; }

# Debug
bw status

if ! bw login --check; then
  bw login
# The vault unlocks once you login. It can however happen
# that you're already logged in, but the vault is locked.
elif ! bw unlock --check; then
  BW_SESSION="$(bw unlock --raw)"
  export BW_SESSION
fi

# Debug
bw unlock --check

# Pull the latest vault data from server
bw sync

# Get the item id first
ITEM_ID=$(bw get item "${BW_ITEM}" | jq -r .id)
[[ -z ${ITEM_ID} ]] && { echo >&2 "Couldn't find ${BW_ITEM} in Bitwarden vault"; exit 1; }

# Download all attachments of that item
bw get item "${BW_ITEM}" | jq -r .attachments[].id | xargs -L1 bw get attachment --itemid "${ITEM_ID}" --output "${PATH_TO_SECRETS}"
