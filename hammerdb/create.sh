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
    export RESOURCE_GROUP_NAME=${driver_rg}
    sh ./delete-resource-group.sh
}

# trap cleanup EXIT

hammerdb_dir="${0%/*}"
cd ${hammerdb_dir}
topdir=${hammerdb_dir}/..

cluster_rg=CITUS_TEST_CLUSTER_RG1
driver_rg=HAMMERDB_DRIVER_RG1

export RESOURCE_GROUP_NAME=${driver_rg}
cd ${topdir}/drivernode
./create-drivernode.sh

export RESOURCE_GROUP_NAME=${cluster_rg}
cd ${topdir}/azure
./create-cluster.sh


cluster_ip=$(az group deployment show -g ${cluster_rg} -n azuredeploy --query properties.outputs.publicIP.value)
# remove the quotes 
cluster_ip=$(echo ${cluster_ip} | cut -d "\"" -f 2)
echo ${cluster_ip}

driver_ip=$(az group deployment show -g ${driver_rg} -n azuredeploy --query properties.outputs.publicIP.value)
# remove the quotes 
driver_ip=$(echo ${driver_ip} | cut -d "\"" -f 2)
echo ${driver_ip}

ssh-keyscan -H ${cluster_ip} >> ~/.ssh/known_hosts
ssh-keyscan -H ${driver_ip} >> ~/.ssh/known_hosts
chmod 600 ~/.ssh/known_hosts

export RESOURCE_GROUP_NAME=${driver_rg}
sh ${topdir}/azure/delete-security-rule.sh

# ssh with non-interactive mode does not source bash profile, so we will need to do it ourselves here.
ssh -o "StrictHostKeyChecking no" -A pguser@${driver_ip} "source ~/.bash_profile;/home/pguser/test-automation/drivernode/setup.sh ${cluster_ip}"

export RESOURCE_GROUP_NAME=${cluster_rg}
sh ${topdir}/azure/delete-security-rule.sh

# ssh with non-interactive mode does not source bash profile, so we will need to do it ourselves here.
ssh -o "StrictHostKeyChecking no" -A pguser@${cluster_ip} "source ~/.bash_profile;fab use.postgres:12.1 use.citus:master setup.basic_testing setup.hammerdb:${driver_ip}"