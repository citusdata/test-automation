#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

# in redhat we need to enable default port for postgres
firewall-cmd --add-port=5432/tcp

# install pip since we will use it to install dependencies
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py

# install git to clone the repository
yum install -y git screen

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
mount ${DEV} /home/${TARGET_USER}/
rsync -aXS /tmp/home_copy/. /home/${TARGET_USER}/.

# add the username to sudoers so that sudo command does not prompt password.
# We do not want the password prompt, because we want to run tests without any user input
echo '${TARGET_USER}     ALL=(ALL) NOPASSWD:ALL' >>/etc/sudoers

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

wget "https://github.com/TPC-Council/HammerDB/releases/download/v3.3/HammerDB-3.3-Linux.tar.gz"
tar -zxvf HammerDB-3.3-Linux.tar.gz

EOSU