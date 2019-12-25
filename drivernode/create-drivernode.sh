#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u / set -o nounset
# exit immediately if a command fails
set -e

## Set mydir to the directory containing the script
## The ${var%pattern} format will remove the shortest match of
## pattern from the end of the string. Here, it will remove the
## script's name,. leaving only the directory. 
driverdir="${0%/*}"
cd ${driverdir}

regions=(eastus southcentralus westus2)

size=${#regions[@]}
index=$(($RANDOM % $size))
random_region=${regions[$index]}

rg=${RESOURCE_GROUP_NAME}
region=${AZURE_REGION:=$random_region}
echo ${region}
az group create -l ${region} -n ${rg}

public_key=$(cat ~/.ssh/id_rsa.pub)

start_time=`date +%s`
echo "waiting a long time to create cluster, this might take up to 30 mins depending on your cluster size"

# if this is run on a job, use the branch for the job, otherwise use master(running in local or remote without a job)
# store the branch name in a file so that target user can read it. Target user cannot see the envionment variables because
# we use login option in su and -p(preserving environment variables) cannot be used with login. We need to use login option
# so that $HOME, $PATH are set to the target users $HOME and $PATH.
export BRANCH=${CIRCLE_BRANCH:=hammerdb}

az group deployment create -g ${rg} --template-file azuredeploy.json --parameters @azuredeploy.parameters.json --parameters sshPublicKey="${public_key}" branchName="$BRANCH"

end_time=`date +%s`
echo execution time was `expr $end_time - $start_time` s.
