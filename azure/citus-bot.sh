#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

source commons.sh

# generate PEM to use to ssh into the Azure VM-s
ssh-keygen -m PEM -b 2048 -t rsa -f ~/.ssh/vm-key -q -N ""
eval `ssh-agent -s`

# add key for azure VM
ssh-add ~/.ssh/vm-key

# add the the default key in order to forward it with
# ssh agent forwarding to allow the Azure VM-s to pull the
# test automation repo
# ssh-add

function cleanup {
    sh ./delete-resource-group.sh
}

trap cleanup EXIT

export RESOURCE_GROUP_NAME="$1"

./create-cluster.sh

ssh_port=$(rg_get_ssh_port ${RESOURCE_GROUP_NAME})
public_ip=$(rg_get_public_ip ${RESOURCE_GROUP_NAME})

echo ${public_ip}

ssh_execute ${public_ip} ${ssh_port} 'echo "'$RESULT_REPO_ACCESS_TOKEN'" > /tmp/result-repo-token'

echo "running tests in remote"
# ssh with non-interactive mode does not source bash profile, so we will need to do it ourselves here.
ssh_execute ${public_ip} ${ssh_port} "source ~/.bash_profile;/home/pguser/test-automation/azure/run-all-tests.sh ${RESOURCE_GROUP_NAME}"

