#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e

echo ${RESOURCE_GROUP_NAME}

# get local public ip 
local_public_ip=$(curl https://ipinfo.io/ip)
# update the rule for custom ssh port with the current local ip (as the local ip could change)
az network nsg rule update --name customSshPort --nsg-name networkSecurityGroup1 --resource-group "$RESOURCE_GROUP_NAME" --source-address-prefixes "${local_public_ip}"
