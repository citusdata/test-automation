#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e

TARGET_USER=pguser

echo ${GIT_USERNAME} > /tmp/git_username
echo ${GIT_TOKEN} > /tmp/git_token

su --login ${TARGET_USER} <<'EOSU'

GIT_USERNAME=$(</tmp/git_username)
GIT_TOKEN=$(</tmp/git_token)

git config --global credential.helper store
cd $HOME
mkdir -p .dummy
cd .dummy
# this is to cache github username and token so that later usages wont ask for username password
git clone https://${GIT_USERNAME}:${GIT_TOKEN}@github.com/citusdata/release-test-results

EOSU

rm /tmp/git_username
rm /tmp/git_token