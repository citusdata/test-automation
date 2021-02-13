#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x
# exit if left size of pipe failed
set -o pipefail

coordinator_private_ip=$1
pub_key=$(ssh-add -L | head -n 1)
if [ -z "$pub_key" ]; then
    echo "ERROR: no keys were added to ssh-agent with ssh-add (ssh-add -L returned empty result)"
    exit 1
fi
# shellcheck disable=SC2029
ssh -o "StrictHostKeyChecking no" -A "${coordinator_private_ip}" "echo ${pub_key} >> ~/.ssh/authorized_keys"
