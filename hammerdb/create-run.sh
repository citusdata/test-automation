#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

is_tpcc=${IS_TPCC:=true} # set to true if you want tpcc to be run, otherwise set to false
is_ch=${IS_CH:=false} # set to true if you want ch benchmark to be run, otherwise set to false
username=pguser # username of the database
hammerdb_version=3.3
hammerdb_branch=hammerdb40 # for hammerdb 3.3 use hammerdb33, for hammerdb 4.0 use hammerdb40

# ssh_execute is used to run a command multiple times on ssh, this is because we sometimes get timeouts 
# while trying to ssh, and it shouldn't make the script fail. If a command actually fails, it will always
# fail no matter how many times we try.
ssh_execute() {
   ip=$1
   shift;
   command=$*
   n=0
   until [ $n -ge 4 ]
   do
      # delete the security before each try
      sh "${topdir}"/azure/delete-security-rule.sh
      ssh -o "StrictHostKeyChecking no" -A pguser@"${ip}" "source ~/.bash_profile;${command}" && break
      n=$((n+1))
   done

   if [ $n == 4 ]; then
      exit 1
   fi
}

hammerdb_dir="${0%/*}"
cd "${hammerdb_dir}"
export topdir=${hammerdb_dir}/..

cluster_rg="${RESOURCE_GROUP_NAME}"

# https://stackoverflow.com/questions/1593051/how-to-programmatically-determine-the-current-checked-out-git-branch
branch_name=$(git symbolic-ref -q HEAD)
branch_name=${branch_name##refs/heads/}
branch_name=${branch_name:-HEAD}

cd "${topdir}"/hammerdb
# create the cluster with driver node
./create.sh


cluster_ip=$(az group deployment show -g "${cluster_rg}" -n azuredeploy --query properties.outputs.publicIP.value)
# remove the quotes 
cluster_ip=$(echo "${cluster_ip}" | cut -d "\"" -f 2)
echo "${cluster_ip}"

coordinator_private_ip=$(az group deployment show -g "${cluster_rg}" -n azuredeploy --query properties.outputs.coordinatorPrivateIP.value)
# remove the quotes 
coordinator_private_ip=$(echo "${coordinator_private_ip}" | cut -d "\"" -f 2)
echo "${coordinator_private_ip}"


driver_ip=$(az group deployment show -g "${cluster_rg}" -n azuredeploy --query properties.outputs.driverPublicIP.value)
# remove the quotes 
driver_ip=$(echo "${driver_ip}" | cut -d "\"" -f 2)
echo "${driver_ip}"

driver_private_ip=$(az group deployment show -g "${cluster_rg}" -n azuredeploy --query properties.outputs.driverPrivateIP.value)
# remove the quotes 
driver_private_ip=$(echo "${driver_private_ip}" | cut -d "\"" -f 2)
echo "${driver_private_ip}"

# add the cluster and driver ip to our known host so that they don't prompt any verification.
ssh-keyscan -H "${cluster_ip}" >> ~/.ssh/known_hosts
ssh-keyscan -H "${driver_ip}" >> ~/.ssh/known_hosts
# just to be sure, the permission of known_hosts should be 600, otherwise it is ignored.
chmod 600 ~/.ssh/known_hosts

# add the public key of coordinator to the driver node so that driver can connect to the coordinator 
# without getting permission error.
ssh_execute "${driver_ip}" "/home/pguser/test-automation/hammerdb/send_pubkey.sh ${coordinator_private_ip}" 

set +e
# run hammerdb test, this will be run in a detached session.
ssh_execute "${driver_ip}" "screen -d -m -L /home/pguser/test-automation/hammerdb/run_all.sh ${coordinator_private_ip} ${driver_private_ip} ${branch_name} ${is_tpcc} ${is_ch} ${username} ${hammerdb_version} ${hammerdb_branch} ${cluster_rg}"
set -e

echo "Successfully started the benchmark(There can still be runtime errors)!"
