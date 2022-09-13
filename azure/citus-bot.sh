#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

source commons.sh
# source instead of just calling to override the ssh-agent created
# by CircleCI
source ./add-sshkey.sh

function cleanup {
    sh ./delete-resource-group.sh
}

trap cleanup EXIT

export RESOURCE_GROUP_NAME="$1"

./create-cluster.sh

ssh_port=$(rg_get_ssh_port ${RESOURCE_GROUP_NAME})
public_ip=$(rg_get_public_ip ${RESOURCE_GROUP_NAME})

echo ${public_ip}

vm_add_public_ip_to_known_hosts ${public_ip} ${ssh_port}

echo "running tests in remote"
# ssh with non-interactive mode does not source bash profile, so we will need to do it ourselves here.
ssh_execute ${public_ip} ${ssh_port} "source ~/.bash_profile;/home/pguser/test-automation/azure/run-all-tests.sh ${RESOURCE_GROUP_NAME}"

