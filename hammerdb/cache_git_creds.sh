#!/bin/bash

# this file puts git username and token to a temporary file so that
# a user can read them from a file and clone a private repository 
# with caching enabled. After that this user can safely clone private 
# repositories without the need for password.

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e


TARGET_USER=pguser

echo "${GIT_USERNAME}" > /tmp/git_username
echo "${GIT_TOKEN}" > /tmp/git_token

su --login ${TARGET_USER} <<'EOSU'

GIT_USERNAME=$(</tmp/git_username)
GIT_TOKEN=$(</tmp/git_token)

git config --global credential.helper store
cd $HOME
# remove .dummy if it exists
rm -rf .dummy
mkdir -p .dummy
cd .dummy
# this is to cache github username and token so that later usages wont ask for username password
git clone https://${GIT_USERNAME}:${GIT_TOKEN}@github.com/citusdata/release-test-results --single-branch

EOSU

# remove the username and token, even if they weren't removed it should be safe as this is 
# in tmp directory and it is on an azure server.
rm /tmp/git_username
rm /tmp/git_token