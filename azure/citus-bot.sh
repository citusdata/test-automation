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

rg=$1
export RESOURCE_GROUP_NAME=${rg}

if [ "$rg" != "citusbot_valgrind_test_resource_group" ]; then
    # If running valgrind tests, do not run cleanup function
    # This is because, as valgrind tests requires too much time to run,
    # we start valgrind tests via nohup in ci. Hence ssh session 
    # will immediately be closed just after the fabric command is run
    #
    # We have a seperate job to terminate the machine and push the results
    trap cleanup EXIT
else
    # If running valgrind tests, export VALGRIND_TEST to be 1 to ensure
    # only coordinator instance is created in create-cluster script
    export VALGRIND_TEST=1
fi 

./create-cluster.sh

public_ip=$(az group deployment show -g ${rg} -n azuredeploy --query properties.outputs.publicIP.value)
# remove the quotes 
public_ip=$(echo ${public_ip} | cut -d "\"" -f 2)
echo ${public_ip}
ssh-keyscan -H ${public_ip} >> ~/.ssh/known_hosts
chmod 600 ~/.ssh/known_hosts

sh ./delete-security-rule.sh

echo "adding public ip to known hosts in remote"
ssh -o "StrictHostKeyChecking no" -A pguser@${public_ip} "ssh-keyscan -H ${public_ip} >> /home/pguser/.ssh/known_hosts"

echo "running tests in remote"

# ssh with non-interactive mode does not source bash profile, so we will need to do it ourselves here.
ssh -o "StrictHostKeyChecking no" -A pguser@${public_ip} "source ~/.bash_profile;/home/pguser/test-automation/azure/run-all-tests.sh ${rg};"
