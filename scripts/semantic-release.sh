#!/usr/bin/env bash

set -e

PACKAGES="semantic-release@19 @semantic-release/git@10 @semantic-release/changelog@6 @semantic-release/exec@6"
OPTIONS=$(echo $PACKAGES | sed 's/[^ ]* */--package=&/g')
npx --yes $OPTIONS -- semantic-release --dry-run --no-ci
