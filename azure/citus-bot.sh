#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

source add-sshkey.sh

# ssh_execute tries to send the given command over the given connection multiple times.
# It uses the custom ssh port 3456.
ssh_execute() {
   ip=$1
   shift;
   command=$@
   n=0
   until [ $n -ge 10 ]
   do
      ssh -o "StrictHostKeyChecking no" -A -p "${ssh_port}" pguser@${ip} "source ~/.bash_profile;${command}" && break
      rc=$? # get return code
      if [ $rc -ne 255 ] ; then
         # if the error code is not 255 we didn't get a connection error.
         exit 1
      fi
      n=$[$n+1]
   done

   if [ $n == 10 ]; then
      exit 1
   fi
}

function cleanup {
    sh ./delete-resource-group.sh
}

trap cleanup EXIT

rg=$1
export RESOURCE_GROUP_NAME=${rg}

if [ "$rg" == "citusbot_valgrind_test_resource_group" ]; then
    # If running valgrind tests, export VALGRIND_TEST to be 1 to ensure
    # only coordinator instance is created in create-cluster script
    export VALGRIND_TEST=1
fi

./create-cluster.sh

if [ "$rg" == "citusbot_valgrind_test_resource_group" ]; then
    # If running valgrind tests, do not run cleanup function
    # This is because, as valgrind tests requires too much time to run,
    # we start valgrind tests via nohup in ci. Hence ssh session
    # will immediately be closed just after the fabric command is run
    trap - EXIT
fi

ssh_port=$(az deployment group show -g "${RESOURCE_GROUP_NAME}" -n azuredeploy --query properties.outputs.customSshPort.value)
# remove the quotes 
ssh_port=$(echo "${ssh_port}" | cut -d "\"" -f 2)

public_ip=$(az deployment group show -g ${rg} -n azuredeploy --query properties.outputs.publicIP.value)
# remove the quotes 
public_ip=$(echo ${public_ip} | cut -d "\"" -f 2)
echo ${public_ip}

echo "adding public ip to known hosts in remote"
ssh_execute ${public_ip} "ssh-keyscan -H ${public_ip} >> /home/pguser/.ssh/known_hosts"
echo "running tests in remote"
# ssh with non-interactive mode does not source bash profile, so we will need to do it ourselves here.
ssh_execute ${public_ip} "source ~/.bash_profile;/home/pguser/test-automation/azure/run-all-tests.sh ${rg}"

