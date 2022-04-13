#!/usr/bin/bash

# Script to
# - login to Bitwarden and/or unlock the vault
# - download all files attached to
#   secrets-${SERVICE}-${DEPLOYMENT} and secrets-tls-certs notes
#   into secrets/${SERVICE}/${DEPLOYMENT}/
# Example usage:
# SERVICE=packit DEPLOYMENT=stg PATH_TO_SECRETS=/tmp/xyz/ ./scripts/download_secrets.sh

# If you're about to run this script more times,
# you better run 'bw login || bw unlock' yourself and export the returned BW_SESSION
# so that this script doesn't ask you for the master password every time.
# For example I (jpopelka) have this in my ~/.bashrc
# alias bwunlock='bw unlock --check || export BW_SESSION="$(bw unlock --raw)"'

# If run via 'make deploy', you can use this (on your own risk) to
# not download secrets again, if you just did it.
[[ -n "${SKIP_SECRETS_SYNC}" || -n "${SSS}" ]] && { echo "Not downloading secrets"; exit 0; }

# Where to download the files
DEFAULT_PATH_TO_SECRETS="secrets/${SERVICE}/${DEPLOYMENT}/"

# Set default values if not set already
: "${SERVICE:=packit}"
: "${DEPLOYMENT:=dev}"
[[ "${DEPLOYMENT}" == "dev" ]] && { echo "Not downloading secrets for DEPLOYMENT==dev"; exit 0; }
: "${PATH_TO_SECRETS:=$DEFAULT_PATH_TO_SECRETS}"

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
bw unlock --check || { echo >&2 "Failed to unlock vault"; exit 1; }

# Pull the latest vault data from server
bw sync

download_attachments_of_item() {
  # Parameter is the name of the shared (Bitwarden vault) item,
  # which contains the secret files as attachments.

  # Get the item id first
  ITEM_ID=$(bw get item "${1}" | jq -r .id)
  [[ -z ${ITEM_ID} ]] && { echo >&2 "Couldn't find ${1} in Bitwarden vault"; exit 1; }

  # Download all attachments of that item
  bw get item "${1}" | jq -r .attachments[].id | xargs -L1 bw get attachment --itemid "${ITEM_ID}" --output "${PATH_TO_SECRETS}"
}

download_attachments_of_item "secrets-${SERVICE}-${DEPLOYMENT}"
download_attachments_of_item "secrets-tls-certs"
