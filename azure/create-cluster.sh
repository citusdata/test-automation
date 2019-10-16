#!/bin/bash

rg=${RESOURCE_GROUP_NAME}

az group create -l eastus -n ${rg}

az group deployment create -g ${rg} --template-file azuredeploy.json --parameters azuredeploy.parameters.json --debug

connection_string=$(az group deployment show -g ${rg} -n azuredeploy --query properties.outputs.ssh.value)

echo "run './delete_security_rule.sh' to temporarily disable security rule, and connect with:"
echo ${connection_string}