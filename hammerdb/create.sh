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
cd "${driverdir}"

regions=(eastus southcentralus westus2)

size=${#regions[@]}
index=$((RANDOM % size))
random_region=${regions[$index]}

rg="${RESOURCE_GROUP_NAME}"
# if region is provided, use that. If not use the random region.
region=${AZURE_REGION:=$random_region}
echo "${region}"
az group create -l "${region}" -n "${rg}"

# get our public key programmatically so that users don't have to enter it manually.
pub_key=$(ssh-add -L | head -n 1)
if [ -z "$pub_key" ]; then
    echo "ERROR: no keys were added to ssh-agent with ssh-add (ssh-add -L returned empty result)"
    exit 1
fi

start_time=$(date +%s)
echo "waiting a long time to create cluster, this might take up to 30 mins depending on your cluster size"

# https://stackoverflow.com/questions/1593051/how-to-programmatically-determine-the-current-checked-out-git-branch
branch_name=$(git symbolic-ref -q HEAD)
branch_name=${branch_name##refs/heads/}
branch_name=${branch_name:-HEAD}

# store the branch name in a file so that target user can read it. Target user cannot see the envionment variables because
# we use login option in su and -p(preserving environment variables) cannot be used with login. We need to use login option
# so that $HOME, $PATH are set to the target users $HOME and $PATH.
export BRANCH=${branch_name}

az group deployment create -g "${rg}" --template-file azuredeploy.json --parameters @azuredeploy.parameters.json --parameters sshPublicKey="${pub_key}" branchName="$BRANCH" git_username="${GIT_USERNAME}" git_token="${GIT_TOKEN}"

end_time=$(date +%s)
echo execution time was $((end_time - start_time)) s.
