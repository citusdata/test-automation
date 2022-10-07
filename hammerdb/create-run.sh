#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

is_tpcc=${IS_TPCC:=true} # set to true if you want tpcc to be run, otherwise set to false
is_ch=${IS_CH:=false} # set to true if you want ch benchmark to be run, otherwise set to false
username=pguser # username of the database
hammerdb_version=4.4 # (4.4+ recommended) find available versions in download-hammerdb.sh

# ssh_execute is used to run a command multiple times on ssh, this is because we sometimes get timeouts
# while trying to ssh, and it shouldn't make the script fail. If a command actually fails, it will always
# fail no matter how many times we try.
ssh_execute() {
   ip=$1
   shift;
   command=$*
   n=0
   until [ $n -ge 10 ]
   do
      ssh -o "StrictHostKeyChecking no" -A -p "$ssh_port" pguser@"${ip}" "source ~/.bash_profile;${command}" && break
      n=$((n+1))
   done

   if [ $n == 10 ]; then
      exit 1
   fi
}

get_cluster_output() {
   output_name=$1
   value=$(az deployment group show -g "${cluster_rg}" -n azuredeploy --query properties.outputs."${output_name}".value)
   # remove the quotes
   value=$(echo "${value}" | cut -d "\"" -f 2)
   echo "$value"
}

hammerdb_dir="${0%/*}"
cd "${hammerdb_dir}"
export topdir=${hammerdb_dir}/..

cluster_rg="${RESOURCE_GROUP_NAME}"

# https://stackoverflow.com/questions/1593051/how-to-programmatically-determine-the-current-checked-out-git-branch
branch_name=$(git symbolic-ref -q HEAD)
branch_name=${branch_name##refs/heads/}
branch_name=${branch_name:-HEAD}

cd "${topdir}"/hammerdb
# create the cluster with driver node
./create.sh

ssh_port=$(get_cluster_output customSshPort)

cluster_ip=$(get_cluster_output publicIP)
echo "${cluster_ip}"

coordinator_private_ip=$(get_cluster_output coordinatorPrivateIP)
echo "${coordinator_private_ip}"

driver_ip=$(get_cluster_output driverPublicIP)
echo "${driver_ip}"

driver_private_ip=$(get_cluster_output driverPrivateIP)
echo "${driver_private_ip}"

# add the public key of coordinator to the driver node so that driver can connect to the coordinator
# without getting permission error.
ssh_execute "${driver_ip}" "/home/pguser/test-automation/hammerdb/send_pubkey.sh ${coordinator_private_ip}"

set +e
# run hammerdb test, this will be run in a detached session.
ssh_execute "${driver_ip}" "screen -d -m -L /home/pguser/test-automation/hammerdb/run_all.sh ${coordinator_private_ip} ${driver_private_ip} ${branch_name} ${is_tpcc} ${is_ch} ${username} ${hammerdb_version} ${cluster_rg}"
set -e

echo "Successfully started the benchmark(There can still be runtime errors)!"
