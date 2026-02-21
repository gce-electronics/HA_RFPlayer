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
PYPROJECT="${ROOT}/pyproject.toml"
SCRIPT_DIR="$(dirname "$0")"

# Sync dependencies from pyproject.toml to manifest.json
python3 "${SCRIPT_DIR}/update_manifest.py" "${PYPROJECT}" "${MANIFEST}" "${NEXT_VERSION}"

cd "${RFPLAYER_COMPONENT}" && zip ${ZIPFILE} -x "*.pyc" -r ./
