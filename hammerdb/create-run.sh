#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x


function cleanup {
    cd ${topdir}/azure
    export RESOURCE_GROUP_NAME=${cluster_rg}
    sh ./delete-resource-group.sh
}

ssh_execute() {
   ip=$1
   shift;
   command=$@
   n=0
   until [ $n -ge 4 ]
   do
      sh ${topdir}/azure/delete-security-rule.sh
      ssh -o "StrictHostKeyChecking no" -A pguser@${ip} "source ~/.bash_profile;${command}" && break
      n=$[$n+1]
   done

   if [ $n == 4 ]; then
      exit 1
   fi
}

# trap cleanup EXIT

regions=(eastus southcentralus westus2)

size=${#regions[@]}
index=$(($RANDOM % $size))
random_region=${regions[$index]}

hammerdb_dir="${0%/*}"
cd ${hammerdb_dir}
export topdir=${hammerdb_dir}/..

cluster_rg=CITUS_TEST_CLUSTER_RG32

branch_name=hammerdb

export RESOURCE_GROUP_NAME=${cluster_rg}
cd ${topdir}/hammerdb
./create.sh


cluster_ip=$(az group deployment show -g ${cluster_rg} -n azuredeploy --query properties.outputs.publicIP.value)
# remove the quotes 
cluster_ip=$(echo ${cluster_ip} | cut -d "\"" -f 2)
echo ${cluster_ip}

coordinator_private_ip=$(az group deployment show -g ${cluster_rg} -n azuredeploy --query properties.outputs.coordinatorPrivateIP.value)
# remove the quotes 
coordinator_private_ip=$(echo ${coordinator_private_ip} | cut -d "\"" -f 2)
echo ${coordinator_private_ip}


driver_ip=$(az group deployment show -g ${cluster_rg} -n azuredeploy --query properties.outputs.driverPublicIP.value)
# remove the quotes 
driver_ip=$(echo ${driver_ip} | cut -d "\"" -f 2)
echo ${driver_ip}

driver_private_ip=$(az group deployment show -g ${cluster_rg} -n azuredeploy --query properties.outputs.driverPrivateIP.value)
# remove the quotes 
driver_private_ip=$(echo ${driver_private_ip} | cut -d "\"" -f 2)
echo ${driver_private_ip}

ssh-keyscan -H ${cluster_ip} >> ~/.ssh/known_hosts
ssh-keyscan -H ${driver_ip} >> ~/.ssh/known_hosts
chmod 600 ~/.ssh/known_hosts


set +e

ssh_execute ${driver_ip} "/home/pguser/test-automation/hammerdb/setup.sh ${coordinator_private_ip} ${branch_name}"
for config_file in "${topdir}/fabfile/hammerdb_confs"/*
do
  # get the file name from absolute path 
  config_file=`basename $config_file`

  ssh_execute ${cluster_ip} "fab setup.hammerdb:${config_file},driver_ip=${driver_private_ip}"
  ssh_execute ${driver_ip} "/home/pguser/test-automation/hammerdb/build-and-run.sh ${coordinator_private_ip} ${config_file}"
done

ssh_execute ${driver_ip} "/home/pguser/test-automation/hammerdb/upload-results.sh ${branch_name}"
set -e
