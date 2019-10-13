#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# fail in a pipeline if any of the commands fails
set -o pipefail

# in redhat we need to enable default port for postgres
firewall-cmd --add-port=5432/tcp

# install pip since we will use it to install dependencies
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python get-pip.py

# install git to clone the repository 
yum install -y git

# this is the username in our instances
TARGET_USER=pguser    

# add the username to sudoers so that sudo command does not prompt password.
# We do not want the password prompt, because we want to run tests without any user input
echo '${TARGET_USER}     ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

setup_user() {

  # add pg and local binaries to the path
  echo "export PATH=${HOME}/pg-latest/bin/:${HOME}/.local/bin/:$PATH" >> ${HOME}/.bash_profile

  cd ${HOME} && git clone https://github.com/citusdata/test-automation.git

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
}


su - ${TARGET_USER} << 'EOSU'
setup_user
EOSU

sh ./find_private_ips.sh "$@"
