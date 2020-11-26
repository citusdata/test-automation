#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

# in redhat we need to enable default port for postgres
# We don't exit on this command because if we are on centos, the firewall
# might not be active, but this also enables switching to redhat easily.
firewall-cmd --add-port=5432/tcp || true 

# fail in a pipeline if any of the commands fails
set -o pipefail

rpm -Uvh https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm
# install git to clone the repository
yum install -y git screen tmux htop python

# install pip since we will use it to install dependencies
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py

# this is the username in our instances
TARGET_USER=pguser

#A set of disks to ignore from partitioning and formatting
BLACKLIST="/dev/sda|/dev/sdb"
DEVS=($(ls -1 /dev/sd*|egrep -v "${BLACKLIST}"|egrep -v "[0-9]$"))
read DEV __ <<< ${DEVS}

# attach disk and mount it for data
mkfs.ext4 -F ${DEV}
mv /home/${TARGET_USER}/ /tmp/home_copy
mkdir -p /home/${TARGET_USER}
mount -o barrier=0 ${DEV} /home/${TARGET_USER}/
rsync -aXS /tmp/home_copy/. /home/${TARGET_USER}/.


# add the username to sudoers so that sudo command does not prompt password.
# We do not want the password prompt, because we want to run tests without any user input
echo '${TARGET_USER}     ALL=(ALL) NOPASSWD:ALL' >>/etc/sudoers


BRANCH=$5

echo ${BRANCH} > /tmp/branch_name

su --login ${TARGET_USER} <<'EOSU'
 # add pg and local binaries to the path
  echo "export PATH=${HOME}/pg-latest/bin/:${HOME}/.local/bin/:$PATH" >> ${HOME}/.bash_profile

  branch=$(</tmp/branch_name)
  cd ${HOME} && git clone --branch ${branch} https://github.com/citusdata/test-automation.git

  # create a link for fabfile in home since we use it from home
  ln -s ${HOME}/test-automation/fabfile ${HOME}/fabfile

  # source the auto completion of fab
  echo "source ${HOME}/test-automation/cloudformation/fab" >> ${HOME}/.bash_profile

  # install requirements for tests
  pip install -r ${HOME}/test-automation/fabfile/requirements.txt --user

  # generate public key and add it to authorized keys so that sshing localhost does not ask password
  echo | ssh-keygen -P "" -t rsa
  cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
  chmod 600 ~/.ssh/authorized_keys

  # https://gist.github.com/martijnvermaat/8070533
  echo "setenv SSH_AUTH_SOCK ${HOME}/.ssh/ssh_auth_sock" > ${HOME}/.screenrc
  echo 'if test "$SSH_AUTH_SOCK" ; then' >> ${HOME}/.ssh/rc
  echo 'ln -sf $SSH_AUTH_SOCK ${HOME}/.ssh/ssh_auth_sock' >> ${HOME}/.ssh/rc
  echo 'fi' >> ${HOME}/.ssh/rc

EOSU

find_private_ips() {
  rpm --import https://packages.microsoft.com/keys/microsoft.asc
  sh -c 'echo -e "[azure-cli]\nname=Azure CLI\nbaseurl=https://packages.microsoft.com/yumrepos/azure-cli\nenabled=1\ngpgcheck=1\ngpgkey=https://packages.microsoft.com/keys/microsoft.asc" > /etc/yum.repos.d/azure-cli.repo'

  yum install -y azure-cli

  mkdir /home/log
  chmod og+rwx /home/log

  LOGS=/home/log/logs.txt

  echo "current user" $(whoami) >>$LOGS

  echo parameters >>$LOGS
  for i; do
    echo $i >>$LOGS
  done

  hostname -I >/home/log/ip_address

  export NODE_ID=$1
  export NODE_COUNT=$2
  export AZURE_STORAGE_ACCOUNT=$3
  export AZURE_STORAGE_KEY=$4


  if [ $NODE_ID -eq 0 ]; then
    echo configuring coordinator >>$LOGS
  else
    echo configuring worker $1 >>$LOGS
  fi

  export CONTAINER_NAME=node-$NODE_ID

  echo container name = $CONTAINER_NAME >>$LOGS
  echo AZURE_STORAGE_ACCOUNT = $AZURE_STORAGE_ACCOUNT >>$LOGS
  echo AZURE_STORAGE_KEY = $AZURE_STORAGE_KEY >>$LOGS

  az storage container create --name $CONTAINER_NAME
  az storage blob upload --container-name $CONTAINER_NAME --file /home/log/logs.txt --name logs.txt
  az storage blob upload --container-name $CONTAINER_NAME --file /home/log/ip_address --name ip_address
  az storage blob upload --container-name $CONTAINER_NAME --file /home/${TARGET_USER}/.ssh/id_rsa.pub --name public_key

  az storage blob list --container-name $CONTAINER_NAME >/home/log/list.txt

  az storage blob download --container-name $CONTAINER_NAME --name logs.txt --file /home/log/downloaded.txt >/home/log/download.log

  # collect all node's ip addresses
  i=1
  while [ $i -lt $NODE_COUNT ]; do
    echo checking if node-$i is up >>$LOGS
    exists=$(az storage blob exists --container-name node-$i --name ip_address -o tsv)
    echo check result = $exists >>$LOGS
    if [ "$exists" = True ]; then
      echo found >>$LOGS
      az storage blob download --container-name node-$i --name ip_address --file /home/log/node-$i-ip-address
      cat /home/log/node-$i-ip-address >>/home/${TARGET_USER}/test-automation/worker-instances
      i=$(expr $i + 1)
    else
      echo sleeping 5 seconds >>$LOGS
      sleep 5
    fi

  done

  # collect all node's public keys
  i=0
  while [ $i -lt $NODE_COUNT ]; do
    echo checking if node-$i is up >>$LOGS
    exists=$(az storage blob exists --container-name node-$i --name public_key -o tsv)
    echo check result = $exists >>$LOGS
    if [ "$exists" = True ]; then
      echo found >>$LOGS
      az storage blob download --container-name node-$i --name public_key --file /home/log/node-$i-public_key
      cat /home/log/node-$i-public_key >>/home/${TARGET_USER}/.ssh/authorized_keys
      i=$(expr $i + 1)
    else
      echo sleeping 5 seconds >>$LOGS
      sleep 5
    fi

  done

  #now we have all workers reported their ip addresses
  echo "Done" >>$LOGS

}

find_private_ips "$@"
