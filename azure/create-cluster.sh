#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u / set -o nounset
# exit immediately if a command fails
set -e

## Set mydir to the directory containing the script
## The ${var%pattern} format will remove the shortest match of
## pattern from the end of the string. Here, it will remove the
## script's name,. leaving only the directory. 
azuredir="${0%/*}"
cd ${azuredir}

rg=${RESOURCE_GROUP_NAME}
region=${AZURE_REGION:=eastus}
echo ${region}
az group create -l ${region} -n ${rg}

public_key=$(cat ~/.ssh/id_rsa.pub)

start_time=`date +%s`
echo "waiting a long time to create cluster, this might take up to 30 mins depending on your cluster size"

az group deployment create -g ${rg} --template-file azuredeploy.json --parameters @azuredeploy.parameters.json --parameters sshPublicKey="${public_key}" 

end_time=`date +%s`
echo execution time was `expr $end_time - $start_time` s.


connection_string=$(az group deployment show -g ${rg} -n azuredeploy --query properties.outputs.ssh.value)

# remove the quotes 
connection_string=$(echo ${connection_string} | cut -d "\"" -f 2)

echo "run './connect.sh' to connect to the coordinator, or ALTERNATIVELY:"

echo "run './delete-security-rule.sh' to temporarily disable security rule, and connect with:"
echo ${connection_string}