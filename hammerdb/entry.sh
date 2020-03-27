#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

export NODE_ID=$1
export NODE_COUNT=$2
export AZURE_STORAGE_ACCOUNT=$3
export AZURE_STORAGE_KEY=$4
export BRANCH=$5
export GIT_USERNAME=$6
export GIT_TOKEN=$7

# driver node is the last node.
if [[ $(( NODE_COUNT - 1 )) == "$NODE_ID" ]]; then
   ./driver-init.sh "$BRANCH"
else
   ./init.sh "$NODE_ID" $(( NODE_COUNT - 1 )) "$AZURE_STORAGE_ACCOUNT" "$AZURE_STORAGE_KEY" "$BRANCH" 
fi

./cache_git_creds.sh



