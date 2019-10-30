#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x


rg=citusbot_test_resource_group
export RESOURCE_GROUP_NAME=${rg}
sh ./create-cluster.sh


public_ip=$(az group deployment show -g ${rg} -n azuredeploy --query properties.outputs.publicIP.value)
# remove the quotes 
public_ip=$(echo ${public_ip} | cut -d "\"" -f 2)
echo ${public_ip}
ssh-keyscan -H ${public_ip} >> ~/.ssh/known_hosts
chmod 600 ~/.ssh/known_hosts

# these need to be run with sudo.
# echo "Host *" >> /etc/ssh/ssh_config
# echo "ServerAliveInterval 120" >> /etc/ssh/ssh_config

sh ./delete-security-rule.sh

echo "adding public ip to known hosts in remote"
ssh -o "StrictHostKeyChecking no" -A pguser@${public_ip} "ssh-keyscan -H ${public_ip} >> /home/pguser/.ssh/known_hosts"
echo "running tests in remote"
# ssh with non-interactive mode does not source bash profile, so we will need to do it ourselves here.
ssh -o "StrictHostKeyChecking no" -A pguser@${public_ip} "source ~/.bash_profile;sh /home/pguser/test-automation/azure/run_all_tests.sh"

# sh ./delete_resource_group.sh ${rg}
