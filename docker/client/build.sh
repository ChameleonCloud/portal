#!/usr/bin/env bash
# This script builds just the client assets. The reason this script
# exists is to get around issues with the .dockerignore and build context[1];
# very few files affect the client bundle, so we want to avoid doing more
# work than necesary if the build context is modified. We can resolve this
# by creating a temp build context directory, moving just the files we need,
# then building the image from there.
#
# This whole script is doing what .dockerignore should be doing ideally.
# [1]: https://github.com/moby/moby/issues/30018
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
context="$DIR/.build-context"
mkdir -p "$context"
cleanup() {
  echo "Cleaning up temp build context"
  rm -rf "$context"
}
trap cleanup EXIT

find . -path '*/vue/*' ! -path '*/node_modules/*' | cpio -pdm "$context"
for f in package.json vue.config.js yarn.lock; do cp "$f" "$context/"; done
docker build -t client -f "$DIR/Dockerfile" "$context"
