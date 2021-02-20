#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

function cleanup {
    sh ./delete-resource-group.sh
}

export RESOURCE_GROUP_NAME="citusbot_valgrind_test_resource_group"

trap cleanup EXIT

public_ip=$(az group deployment show -g ${RESOURCE_GROUP_NAME} -n azuredeploy --query properties.outputs.publicIP.value)
# remove the quotes 
public_ip=$(echo ${public_ip} | cut -d "\"" -f 2)

echo ${public_ip}

./add-local-ip.sh

echo "adding public ip to known hosts in remote"
ssh -o "StrictHostKeyChecking no" -A pguser@${public_ip} -p 3456 "ssh-keyscan -H ${public_ip} >> /home/pguser/.ssh/known_hosts"
echo "running tests in remote"

# ssh with non-interactive mode does not source bash profile, so we will need to do it ourselves here.
# put an empty success file for valgrind tests under results dir if there are error logs
# push the files under results dir
ssh -o "StrictHostKeyChecking no" -A pguser@${public_ip} -p 3456 \
"source ~/.bash_profile;" \
"sh /home/pguser/test-automation/azure/push-results.sh ${RESOURCE_GROUP_NAME}";
