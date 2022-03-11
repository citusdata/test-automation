#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

source commons.sh

function cleanup {
    sh ./delete-resource-group.sh
}

export RESOURCE_GROUP_NAME="$1"

trap cleanup EXIT

ssh_port=$(rg_get_ssh_port ${RESOURCE_GROUP_NAME})
public_ip=$(rg_get_public_ip ${RESOURCE_GROUP_NAME})

echo ${public_ip}

./add-local-ip.sh

vm_add_public_ip_to_known_hosts ${public_ip} ${ssh_port}

echo "running tests in remote"

# ssh with non-interactive mode does not source bash profile, so we will need to do it ourselves here.
# put an empty success file for valgrind tests under results dir if there are error logs
# push the files under results dir
ssh_execute ${public_ip} ${ssh_port} \
"source ~/.bash_profile;" \
"sh /home/pguser/test-automation/azure/push-results.sh ${RESOURCE_GROUP_NAME}";
