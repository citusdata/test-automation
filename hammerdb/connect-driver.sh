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
dir="${0%/*}"
cd "${dir}"

# get the public ip of driver from the cluster outputs.
public_ip=$(az group deployment show -g "${RESOURCE_GROUP_NAME}" -n azuredeploy --query properties.outputs.driverPublicIP.value)
# remove the quotes 
public_ip=$(echo "${public_ip}" | cut -d "\"" -f 2)

# delete the security rule and connect to the driver node.
sh ../azure/delete-security-rule.sh
ssh -o "StrictHostKeyChecking no" -A pguser@"${public_ip}"