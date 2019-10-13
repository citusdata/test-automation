#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# fail in a pipeline if any of the commands fails
set -o pipefail

prepare_intallation()
{ 

  rpm --import https://packages.microsoft.com/keys/microsoft.asc
  sh -c 'echo -e "[azure-cli]\nname=Azure CLI\nbaseurl=https://packages.microsoft.com/yumrepos/azure-cli\nenabled=1\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" > /etc/yum.repos.d/azure-cli.repo'
  
  yum install -y azure-cli        

  mkdir /home/log
  chmod og+rwx /home/log

  LOGS=/home/log/logs.txt

  echo "current user" `whoami` >> $LOGS

  echo parameters >> $LOGS
  for i; do 
      echo $i >> $LOGS
  done

  hostname -I > /home/log/ip_address

  export NODE_ID=$1
  export NODE_COUNT=$2
  export AZURE_STORAGE_ACCOUNT=$3
  export AZURE_STORAGE_KEY=$4


  if [ $NODE_ID -eq 0 ] ;
    then
      echo configuring coordinator >> $LOGS
    else
      echo configuring worker $1 >> $LOGS
  fi

  export CONTAINER_NAME=node-$NODE_ID

  echo container name = $CONTAINER_NAME >> $LOGS
  echo AZURE_STORAGE_ACCOUNT =  $AZURE_STORAGE_ACCOUNT >> $LOGS
  echo AZURE_STORAGE_KEY = $AZURE_STORAGE_KEY >> $LOGS

  az storage container create --name $CONTAINER_NAME
  az storage blob upload --container-name $CONTAINER_NAME --file /home/log/logs.txt --name logs.txt
  az storage blob upload --container-name $CONTAINER_NAME --file /home/log/ip_address --name ip_address

  az storage blob list --container-name $CONTAINER_NAME > /home/log/list.txt

  az storage blob download --container-name $CONTAINER_NAME --name logs.txt --file /home/log/downloaded.txt > /home/log/download.log


  # collect all node's ip addresses
  i=1
  while [ $i -lt $NODE_COUNT ]
  do
  echo checking if node-$i is up >> $LOGS
  exists=`az storage blob exists --container-name node-$i --name ip_address -o tsv`
  echo check result = $exists >> $LOGS
  if [ "$exists" =  True ]
  then
    echo found >> $LOGS
    az storage blob download --container-name node-$i --name ip_address --file /home/log/node-$i-ip-address
    cat /home/log/node-$i-ip-address >> /home/${TARGET_USER}/test-automation/worker-instances
    i=$(expr $i + 1) 
  else
    echo sleeping 5 seconds >> $LOGS
    sleep 5
  fi

  done

  #now we have all workers reported their ip addresses
  echo "Done" >> $LOGS

}
