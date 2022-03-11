#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

# ssh_execute tries to send the given command over the given connection multiple times.
#  $1 -> public ip of vm
#  $2 -> ssh port of vm
ssh_execute() {
   ip=$1
   ssh_port=$2
   shift 2;
   command=$@
   n=0
   until [ $n -ge 10 ]
   do
      ssh -o "StrictHostKeyChecking no" -A -p "${ssh_port}" pguser@${ip} "source ~/.bash_profile;${command}" && break
      rc=$? # get return code
      if [ $rc -ne 255 ] ; then
         # if the error code is not 255 we didn't get a connection error.
         exit 1
      fi
      n=$[$n+1]
   done

   if [ $n == 10 ]; then
      exit 1
   fi
}

# rg_get_ssh_port returns customSshPort value for the vm created in given resource group
#  $1 -> resource group name
rg_get_ssh_port() {
    rg=$1

    ssh_port=$(az deployment group show -g "${rg}" -n azuredeploy --query properties.outputs.customSshPort.value)
    # remove the quotes
    ssh_port=$(echo "${ssh_port}" | cut -d "\"" -f 2)

    echo $ssh_port
}

# rg_get_ssh_port returns public ip for the vm created in given resource group
#  $1 -> resource group name
rg_get_public_ip() {
    rg=$1

    public_ip=$(az deployment group show -g ${rg} -n azuredeploy --query properties.outputs.publicIP.value)
    # remove the quotes
    public_ip=$(echo ${public_ip} | cut -d "\"" -f 2)

    echo $public_ip
}

# vm_add_public_ip_to_known_hosts adds public ip of the vm to its known hosts file
#  $1 -> public ip of the vm
#  $1 -> ssh port of the vm
vm_add_public_ip_to_known_hosts() {
    public_ip=$1
    ssh_port=$2

    echo "adding public ip to known hosts in remote"
    ssh_execute ${public_ip} ${ssh_port} "ssh-keyscan -H ${public_ip} >> /home/pguser/.ssh/known_hosts"
}
