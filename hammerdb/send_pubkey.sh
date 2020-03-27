#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

coordinator_private_ip=$1
export pub_key=$(cat ~/.ssh/id_rsa.pub)
ssh -o "StrictHostKeyChecking no" -A "${coordinator_private_ip}" "echo ${pub_key} >> ~/.ssh/authorized_keys"
