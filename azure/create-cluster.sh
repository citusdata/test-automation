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

public_key=$(ssh-add -L | head -n1 )

start_time=`date +%s`
echo "waiting a long time to create cluster, this might take up to 30 mins depending on your cluster size"

# if this is run on a job, use the branch for the job, otherwise use master(running in local or remote without a job)
# store the branch name in a file so that target user can read it. Target user cannot see the envionment variables because
# we use login option in su and -p(preserving environment variables) cannot be used with login. We need to use login option
# so that $HOME, $PATH are set to the target users $HOME and $PATH.
export BRANCH=${CIRCLE_BRANCH:=master}

# get local public ip 
local_public_ip=$(curl https://ipinfo.io/ip)

# below is the default create cluster command
CREATE_CLUSTER_COMMAND=(az deployment group create -g ${rg} --template-file azuredeploy.json --parameters @azuredeploy.parameters.json
 --parameters sshPublicKey="${public_key}" branchName="$BRANCH" localPublicIp="$local_public_ip")

# if VALGRIND_TEST variable is not exported, set it to 0
is_valgrind_test=${VALGRIND_TEST:=0}

# if we want to run valgrind tests, lets overwrite numberOfWorkers parameter with 0
if [[ "$is_valgrind_test" != "0" ]]; then
    # be on the safe side, add "--parameters" before "numberOfWorkers" as the order
    # of the parameters in CREATE_CLUSTER_COMMAND may change
    CREATE_CLUSTER_COMMAND+=(--parameters)
    CREATE_CLUSTER_COMMAND+=(numberOfWorkers=0)
fi

echo "DEBUG:" ${CREATE_CLUSTER_COMMAND[@]}
# run CREATE_CLUSTER_COMMAND
"${CREATE_CLUSTER_COMMAND[@]}"

end_time=`date +%s`
echo execution time was `expr $end_time - $start_time` s.


connection_string=$(az deployment group show -g ${rg} -n azuredeploy --query properties.outputs.ssh.value)

# remove the quotes 
connection_string=$(echo ${connection_string} | cut -d "\"" -f 2)

echo "run './connect.sh' to connect to the coordinator, or ALTERNATIVELY RUN THE FOLLOWING:"

echo ${connection_string}
