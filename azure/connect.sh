#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

## Set mydir to the directory containing the script
## The ${var%pattern} format will remove the shortest match of
## pattern from the end of the string. Here, it will remove the
## script's name,. leaving only the directory.
azuredir="${0%/*}"
cd ${azuredir}

public_ip=$(az deployment group show -g ${RESOURCE_GROUP_NAME} -n azuredeploy --query properties.outputs.publicIP.value)
ssh_port=$(az deployment group show -g ${RESOURCE_GROUP_NAME} -n azuredeploy --query properties.outputs.customSshPort.value)

# remove the quotes
public_ip=$(echo ${public_ip} | cut -d "\"" -f 2)
ssh_port=$(echo ${ssh_port} | cut -d "\"" -f 2)

ssh -o "StrictHostKeyChecking no" -A pguser@${public_ip} -p ${ssh_port}
