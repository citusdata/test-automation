#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e

echo ${RESOURCE_GROUP_NAME}

az network nsg rule delete -g ${RESOURCE_GROUP_NAME} --nsg-name networkSecurityGroup1 -n Cleanuptool-Deny-103