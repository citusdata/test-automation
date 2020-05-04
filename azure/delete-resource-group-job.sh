#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

BRANCH=${CIRCLE_BRANCH}

# the resource group name will be after the prefix "delete_resource_group/id_"
# example branch: delete_resource_group/1231123_ch_benchmark_resource_group
resource_group_name=$(echo "$BRANCH" | sed -e "s@delete_resource_group/[0-9]\+_@@g")

export RESOURCE_GROUP_NAME="$resource_group_name"
./delete-resource-group.sh

