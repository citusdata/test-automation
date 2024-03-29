#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u / set -o nounset
# exit immediately if a command fails
set -e

## Set mydir to the directory containing the script
## The ${var%pattern} format will remove the shortest match of
## pattern from the end of the string. Here, it will remove the
## script's name,. leaving only the directory.
azuredir="${0%/*}"
cd ${azuredir}

regions=(eastus southcentralus westus2)

size=${#regions[@]}
index=$(($RANDOM % $size))
random_region=${regions[$index]}

rg=${RESOURCE_GROUP_NAME}
region=${AZURE_REGION:=$random_region}
echo ${region}
az group create -l ${region} -n ${rg}

# given we might have more then one ssh key loaded we simply take the
# first one according to ssh-add as the public key to use for the vm
# we create in azure.
# jobs that run in multiple stages should have the same set of keys
# added to their invocations.
# make sure the key is in rsa format since other formats are not supported
# from Azure
public_key=$(ssh-add -L | grep ssh-rsa | head -n1)

start_time=`date +%s`
echo "waiting a long time to create cluster, this might take up to 30 mins depending on your cluster size"

# if this is run on a job, use the branch for the job, otherwise use the local (running in local or remote without a job)
# store the branch name in a file so that target user can read it. Target user cannot see the envionment variables because
# we use login option in su and -p(preserving environment variables) cannot be used with login. We need to use login option
# so that $HOME, $PATH are set to the target users $HOME and $PATH.

# https://stackoverflow.com/questions/6245570/how-to-get-the-current-branch-name-in-git
current_branch_name=$(git symbolic-ref --short HEAD 2>/dev/null)
export BRANCH=${CIRCLE_BRANCH:=$current_branch_name}

# get local public ip
local_public_ip=$(curl ifconfig.me)

# below is the default create cluster command
CREATE_CLUSTER_COMMAND=(az deployment group create -g ${rg} --template-file azuredeploy.json --parameters @azuredeploy.parameters.json
 --parameters sshPublicKey="${public_key}" branchName="$BRANCH" localPublicIp="$local_public_ip")

# if EXTENSION_TEST variable is not exported, set it to 0
is_extension_test=${EXTENSION_TEST:=0}

# override numberOfWorkers param if it is extension testing
if [ "$is_extension_test" != "0" ]; then
    CREATE_CLUSTER_COMMAND+=(--parameters numberOfWorkers=0)
fi

# if VALGRIND_TEST variable is not exported, set it to 0
is_valgrind_test=${VALGRIND_TEST:=0}

# if we want to run valgrind tests, lets overwrite numberOfWorkers parameter with 0
if [[ "$is_valgrind_test" != "0" ]]; then
    # be on the safe side, add "--parameters" before "numberOfWorkers" as the order
    # of the parameters in CREATE_CLUSTER_COMMAND may change
    CREATE_CLUSTER_COMMAND+=(--parameters numberOfWorkers=0)
fi

# run CREATE_CLUSTER_COMMAND
"${CREATE_CLUSTER_COMMAND[@]}"

end_time=`date +%s`
echo execution time was `expr $end_time - $start_time` s.


connection_string=$(az deployment group show -g ${rg} -n azuredeploy --query properties.outputs.ssh.value)

# remove the quotes
connection_string=$(echo ${connection_string} | cut -d "\"" -f 2)

echo "run './connect.sh' to connect to the coordinator, or ALTERNATIVELY RUN THE FOLLOWING:"

echo ${connection_string}
