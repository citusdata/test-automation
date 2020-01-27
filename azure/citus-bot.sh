#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

ssh_execute() {
   ip=$1
   shift;
   command=$@
   n=0
   until [ $n -ge 4 ]
   do
      sh ./delete-security-rule.sh
      ssh -o "StrictHostKeyChecking no" -A pguser@${ip} "source ~/.bash_profile;${command}" && break
      n=$[$n+1]
   done

   if [ $n == 4 ]; then
      exit 1
   fi
}

function cleanup {
    sh ./delete-resource-group.sh
}

trap cleanup EXIT

rg=$1
export RESOURCE_GROUP_NAME=${rg}
./create-cluster.sh


public_ip=$(az group deployment show -g ${rg} -n azuredeploy --query properties.outputs.publicIP.value)
# remove the quotes 
public_ip=$(echo ${public_ip} | cut -d "\"" -f 2)
echo ${public_ip}
ssh-keyscan -H ${public_ip} >> ~/.ssh/known_hosts
chmod 600 ~/.ssh/known_hosts

sh ./delete-security-rule.sh

echo "adding public ip to known hosts in remote"
ssh_execute ${public_ip} "ssh-keyscan -H ${public_ip} >> /home/pguser/.ssh/known_hosts"
echo "running tests in remote"
# ssh with non-interactive mode does not source bash profile, so we will need to do it ourselves here.
ssh_execute ${public_ip} "source ~/.bash_profile;/home/pguser/test-automation/azure/run-all-tests.sh ${rg}"

