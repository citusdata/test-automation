#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# fail in a pipeline if any of the commands fails
set -o pipefail

rg=citusbot_test_resource_group

sh ./create-cluster.sh ${rg}

public_ip=$(az group deployment show -g ${rg} -n azuredeploy --query properties.outputs.publicIP.value)

sh ./delete_security_rule.sh

ssh -o StrictHostKeyChecking=no -A pguser@${public_ip} sh /home/pguser/test-automation/azure/run_all_tests.sh

sh ./delete_resource_group ${rg}
