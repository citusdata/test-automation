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
yum install -y screen htop patch

# install tmux
yum install -y http://mirror.stream.centos.org/9-stream/BaseOS/x86_64/os/Packages/tmux-3.2a-4.el9.x86_64.rpm

# install & update ca certificates
yum install -y ca-certificates
update-ca-trust -f

# this is the username in our instances
TARGET_USER=pguser

# find data disk by filtering out the first unmounted block device of specified size with no partitions
echo $(lsblk)
DATA_DISK_SIZE=$2
DATA_DISK_SIZE+=G
disks_of_specified_size=($(lsblk --noheadings -o NAME,SIZE,TYPE | awk -v disksize=${DATA_DISK_SIZE} '{ if ($3=="disk" && $2==disksize) { print $1 } }'))
DEV=""
for disk in "${disks_of_specified_size[@]}"; do
  disk_partition_count=$(lsblk --noheadings -o NAME,TYPE | (grep ${disk} || true) | awk '{ if ($2=="part") { print $1 } }' | wc -l)
  disk_unmounted=$(lsblk --noheadings -o NAME,MOUNTPOINT | (grep ${disk} || true) | awk '{ if ($2=="") { print $1 } }' | wc -l)

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

BRANCH=$1

echo ${BRANCH} > /tmp/branch_name

su --login ${TARGET_USER} <<'EOSU'

branch=$(</tmp/branch_name)
cd ${HOME} && git clone --branch ${branch} https://github.com/citusdata/test-automation.git

# https://gist.github.com/martijnvermaat/8070533
echo "setenv SSH_AUTH_SOCK ${HOME}/.ssh/ssh_auth_sock" > ${HOME}/.screenrc
echo 'if test "$SSH_AUTH_SOCK" ; then' >> ${HOME}/.ssh/rc
echo 'ln -sf $SSH_AUTH_SOCK ${HOME}/.ssh/ssh_auth_sock' >> ${HOME}/.ssh/rc
echo 'fi' >> ${HOME}/.ssh/rc

# generate public key and add it to authorized keys so that sshing localhost does not ask password
echo | ssh-keygen -P "" -t rsa
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

EOSU
