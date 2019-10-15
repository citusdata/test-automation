#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# fail in a pipeline if any of the commands fails
set -o pipefail

rg=citusbot_test_resource_group5
export RESOURCE_GROUP_NAME=${rg}
sh ./create-cluster.sh ${rg}

public_ip=$(az group deployment show -g ${rg} -n azuredeploy --query properties.outputs.publicIP.value)

# remove the quotes 
public_ip=$(echo ${public_ip} | cut -d "\"" -f 2)
echo ${public_ip}
ssh-keyscan -H ${public_ip} >> ~/.ssh/known_hosts

sh ./delete_security_rule.sh

ssh -A pguser@${public_ip} sh /home/pguser/test-automation/azure/run_all_tests.sh

# sh ./delete_resource_group.sh ${rg}
