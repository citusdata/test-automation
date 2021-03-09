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

# install pip since we will use it to install dependencies
curl https://bootstrap.pypa.io/pip/2.7/get-pip.py -o get-pip.py
python get-pip.py

rpm -Uvh https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
# install git to clone the repository
# install screen so that we can run commands in a detached session
yum install -y git screen tmux htop

# this is the username in our instances
TARGET_USER=pguser

#A set of disks to ignore from partitioning and formatting
BLACKLIST="/dev/sda|/dev/sdb"
DEVS=($(ls -1 /dev/sd*|egrep -v "${BLACKLIST}"|egrep -v "[0-9]$"))
read DEV __ <<< "${DEVS}"

# attach disk and mount it for data
mkfs.ext4 -F "${DEV}"
mv /home/"${TARGET_USER}"/ /tmp/home_copy
mkdir -p /home/"${TARGET_USER}"
mount -o barrier=0 "${DEV}" /home/"${TARGET_USER}"/
rsync -aXS /tmp/home_copy/. /home/"${TARGET_USER}"/.

# add the username to sudoers so that sudo command does not prompt password.
# We do not want the password prompt, because we want to run tests without any user input
echo '${TARGET_USER}     ALL=(ALL) NOPASSWD:ALL' >>/etc/sudoers

# we will use port 3456 to not hit security rule 103
echo 'Port 3456' >> /etc/ssh/sshd_config
echo 'Port 22' >> /etc/ssh/sshd_config

# necessary for semanage, VMs have secure linux
yum install -y policycoreutils-python
# we need to enable the new port from semanage
semanage port -a -t ssh_port_t -p tcp 3456

# restart ssh service to be able to use the new port
systemctl restart sshd

BRANCH=$1

echo "${BRANCH}" > /tmp/branch_name

su --login "${TARGET_USER}" <<'EOSU'

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
