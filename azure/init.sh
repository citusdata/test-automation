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
firewall-cmd --add-port=3456/tcp || true


# fail in a pipeline if any of the commands fails
set -o pipefail

# install epel repo
yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm

# install git to clone the repository
yum install -y git

# install other utility tools
yum install -y screen htop

# install tmux
yum install -y http://mirror.stream.centos.org/9-stream/BaseOS/x86_64/os/Packages/tmux-3.2a-4.el9.x86_64.rpm

# install & update ca certificates
yum install -y ca-certificates
update-ca-trust -f

# install python3 package manager pip
yum install -y python3-pip

# this is the username in our instances
TARGET_USER=pguser

# find data disk by filtering out the first unmounted block device of specified size with no partitions
echo $(lsblk)
DATA_DISK_SIZE=$6
DATA_DISK_SIZE+=G
# found all disks of given data disk size
disks_of_specified_size=($(lsblk --noheadings -o NAME,SIZE,TYPE | awk -v disksize=${DATA_DISK_SIZE} '{ if ($3=="disk" && $2==disksize) { print $1 } }'))
DEV=""
for disk in "${disks_of_specified_size[@]}"; do
  # found partition count for given disk
  disk_partition_count=$(lsblk --noheadings -o NAME,TYPE | (grep ${disk} || true) | awk '{ if ($2=="part") { print $1 } }' | wc -l)
  # found if given disk is unmounted
  disk_unmounted=$(lsblk --noheadings -o NAME,MOUNTPOINT | (grep ${disk} || true) | awk '{ if ($2=="") { print $1 } }' | wc -l)

  # if given disk has no partition and it is also unmounted, then this is our data disk (we found it)
  if [[ ${disk_partition_count} -eq 0 && ${disk_unmounted} -eq 1 ]]; then
    DEV=/dev/${disk}
    break
  fi
done

if [ "${DEV}" = "" ]; then
  echo "Could not find data disk device!" && exit 1
fi

# attach disk and mount it for data
mkfs -t ext4 ${DEV}
mv /home/${TARGET_USER}/ /tmp/home_copy
mkdir -p /home/${TARGET_USER}
mount -o barrier=0 ${DEV} /home/${TARGET_USER}/
yum install -y rsync
rsync -aXS /tmp/home_copy/. /home/${TARGET_USER}/.


# add the username to sudoers so that sudo command does not prompt password.
# We do not want the password prompt, because we want to run tests without any user input
echo '${TARGET_USER}     ALL=(ALL) NOPASSWD:ALL' >>/etc/sudoers

# we will use port 3456 to not hit security rule 103
echo 'Port 3456' >> /etc/ssh/sshd_config
echo 'Port 22' >> /etc/ssh/sshd_config

# necessary for semanage, VMs have secure linux
yum install -y policycoreutils-python-utils
# we need to enable the new port from semanage
semanage port -a -t ssh_port_t -p tcp 3456

# restart ssh service to be able to use the new port
systemctl restart sshd

BRANCH="fix-epel-repo-install"

echo ${BRANCH} > /tmp/branch_name

su --login ${TARGET_USER} <<'EOSU'
  # add pg and local binaries to the path
  echo "export PATH=${HOME}/pg-latest/bin/:${HOME}/.local/bin/:$PATH" >> ${HOME}/.bash_profile
  # we add the path into bashrc as well, because fab run interactive and nonlogin shell (bash -i -c <command>)
  # only bashrc is read and executed in that scenario
  echo "export PATH=${HOME}/pg-latest/bin/:${HOME}/.local/bin/:$PATH" >> ${HOME}/.bashrc

  branch=$(</tmp/branch_name)
  cd ${HOME} && git clone --branch ${branch} https://github.com/citusdata/test-automation.git

  #### fab setup ####
  # 1) create a link for fabfile in home since we use it from home
  ln -s ${HOME}/test-automation/fabfile ${HOME}/fabfile
  # 2) source the auto completion of fab
  echo "source ${HOME}/test-automation/cloudformation/fab" >> ${HOME}/.bash_profile
  # 3) install requirements for tests
  pip3 install -r ${HOME}/fabfile/requirements.txt --user
  # 4) set PYTHONPATH as fabfile folder to resolve imports when we run fab from other directories
  echo "export PYTHONPATH=${HOME}/fabfile" >> ${HOME}/.bash_profile
  echo "export PYTHONPATH=${HOME}/fabfile" >> ${HOME}/.bashrc
  ####

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
  yum install -y https://packages.microsoft.com/config/rhel/9.0/packages-microsoft-prod.rpm
  yum install -y azure-cli

  mkdir /home/log
  chmod og+rwx /home/log

  LOGS=/home/log/logs.txt

  echo "current user" $(whoami) >>$LOGS

  echo parameters >>$LOGS
  for i; do
    echo $i >>$LOGS
  done

  yum install -y hostname
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
