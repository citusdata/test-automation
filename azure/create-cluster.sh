#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e

rg=${RESOURCE_GROUP_NAME}

az group create -l eastus -n ${rg}

az group deployment create -g ${rg} --template-file azuredeploy.json --parameters azuredeploy.parameters.json

connection_string=$(az group deployment show -g ${rg} -n azuredeploy --query properties.outputs.ssh.value)

# remove the quotes 
connection_string=$(echo ${connection_string} | cut -d "\"" -f 2)

echo "run './delete_security_rule.sh' to temporarily disable security rule, and connect with:"
echo ${connection_string}