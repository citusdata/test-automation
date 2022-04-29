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

# ssh_execute tries to send the given command over the given connection multiple times.
# It uses the custom ssh port 3456.
ssh_execute() {
   ip=$1
   ssh_port=$2
   shift 2;
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

export RESOURCE_GROUP_NAME="$1"

if [[ $RESOURCE_GROUP_NAME =~ citusbot_valgrind_.+_test_resource_group ]]; then
    # If running valgrind tests, export VALGRIND_TEST to be 1 to ensure
    # only coordinator instance is created in create-cluster script
    export VALGRIND_TEST=1
fi

./create-cluster.sh

if [[ $RESOURCE_GROUP_NAME =~ citusbot_valgrind_.+_test_resource_group ]]; then
    # If running valgrind tests, do not run cleanup function
    # This is because, as valgrind tests requires too much time to run,
    # we start valgrind tests via nohup in ci. Hence ssh session
    # will immediately be closed just after the fabric command is run
    trap - EXIT
fi

ssh_port=$(rg_get_ssh_port ${RESOURCE_GROUP_NAME})
public_ip=$(rg_get_public_ip ${RESOURCE_GROUP_NAME})

echo ${public_ip}

vm_add_public_ip_to_known_hosts ${public_ip} ${ssh_port}

echo "running tests in remote"
# ssh with non-interactive mode does not source bash profile, so we will need to do it ourselves here.
ssh_execute ${public_ip} ${ssh_port} "source ~/.bash_profile;/home/pguser/test-automation/azure/run-all-tests.sh ${RESOURCE_GROUP_NAME}"

