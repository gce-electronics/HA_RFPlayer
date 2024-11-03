#!/usr/bin/env bash

set -e

if [ $# -ne 1 ];
then
    echo "Missing version"
    echo "Usage: $0 version"
    exit 1
fi

ROOT=$(realpath "$(dirname "$0")/..")
NEXT_VERSION="$1"
RFPLAYER_COMPONENT="${ROOT}/custom_components/rfplayer"
MANIFEST=${RFPLAYER_COMPONENT}/manifest.json
ZIPFILE="${ROOT}/rfplayer.zip"

cat <<< $(jq ".version=\"${NEXT_VERSION}\"" "${MANIFEST}") > "${MANIFEST}"
cd "${RFPLAYER_COMPONENT}" && zip ${ZIPFILE} -r ./
