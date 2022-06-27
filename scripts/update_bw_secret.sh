#!/usr/bin/bash

# Script to update the attachement of a secret item in Bitwarden
#
# Here is the workflow how to do that:
#
# 1. Make sure your local copy is up to date. For example:
#
#     $ SERVICE=packit DEPLOYMENT=stg make download-secrets
#
# 2. Edit the secret file you want to update, for example:
#
#     $ $EDITOR secrets/packit/stg/packit-service.yaml
#
# 3. Update the secret in Bitwarden. For example:
#
#     $ ./scripts/update_bw_secret.sh secrets/packit/stg/packit-service.yaml
#
# The script figures out which Bitwarden item to edit from the path to the file,
# so that needs to be provided as `secrets/<service>/<deployment>/<file>`.
#
# Nothing happens if the file did not change. The script also helps with
# updating the `! Changelog !`: saves the note in a file, opens the file with
# `$EDITOR` to be edited, and updates the note in Bitwarden.

set -euo pipefail

SECRET_FILE="${1:-}"
SECRET_NAME=$(echo "$SECRET_FILE" | sed -E 's/^secrets\/(.+)\/(.+)\/(.+)$/secrets-\1-\2/')
ATTACHMENT_NAME=$(echo "$SECRET_FILE" | sed -E 's/^secrets\/(.+)\/(.+)\/(.+)$/\3/')

ARG_ERROR="Provide an argument in the form of 'secrets/<service>/<deployment>/<file>'!"
test "$SECRET_FILE" != "$SECRET_NAME" || { echo "$ARG_ERROR"; exit 1; }
test "$SECRET_FILE" != "$ATTACHMENT_NAME" || { echo "$ARG_ERROR"; exit 1; }
test -f "$SECRET_FILE" || { echo "Secret file not found: $SECRET_FILE"; exit 1; }

ITEM_ID=$(bw get item "$SECRET_NAME" | jq -r '.id')
SECRET_NAME=$(bw get item "$SECRET_NAME" | jq -r '.name')
ATTACHMENT_ID=$(bw get item "$ITEM_ID" | jq -r '.attachments[] | select(.fileName=="'${ATTACHMENT_NAME}'") | .id')

test -n "$SECRET_NAME" || { echo "No secret name"; exit 1; }
test -n "$ITEM_ID" || { echo "$SECRET_NAME has no ID"; exit 1; }
test -n "$ATTACHMENT_ID" || { echo "Cannot find $ATTACHMENT_NAME"; exit 1; }

rm -f "${SECRET_FILE}.old"
# Make sure things are up-to-date. 'bw sync' updates the local 'bw' cache, not the files
# already saved.
bw sync
bw get attachment --itemid "$ITEM_ID" --output "${SECRET_FILE}.old" "$ATTACHMENT_NAME" &> /dev/null

if diff "${SECRET_FILE}.old" "$SECRET_FILE"; then
    echo "Attachment '$ATTACHMENT_NAME' of '$SECRET_NAME' is the same as '$SECRET_FILE', skipping..."
else
    echo
    read -p "Do you want to replace attachment '$ATTACHMENT_NAME' of '$SECRET_NAME' with '$SECRET_FILE'? [y/N] " -r
    case $REPLY in
        [Yy]* ) {
            CHANGELOG_ID=$(bw get item "! Changelog !" | jq -r '.id')
            # CHANGELOG_ID=$(bw get item "my-changelog" | jq -r '.id')
            test -n "$CHANGELOG_ID" || { echo "Cannot tell changelog id."; exit 1; }
            bw get item "$CHANGELOG_ID" | jq -r '.notes' > .secrets.changelog.old
            if test -z "$(sed '/^null$/d' .secrets.changelog.old)"; then
                echo "Failed to get changelog, aborting..."
                exit 1
            fi
            cp .secrets.changelog.old .secrets.changelog
            $EDITOR .secrets.changelog

            bw delete attachment --itemid "$ITEM_ID" "$ATTACHMENT_ID" && echo "---> Attachment deleted"
            bw create attachment --itemid "$ITEM_ID" --file "$SECRET_FILE" && echo -e "\n---> Attachment re-created"
            bw get item "$CHANGELOG_ID" | jq ".notes=$(cat .secrets.changelog | jq -sR)" | bw encode | bw edit item "$CHANGELOG_ID"

            rm -f .secrets.changelog .secrets.changelog.old
        };;
        * ) echo "Skipping..."; exit 0;;
    esac

fi

rm -f "${SECRET_FILE}.old"
