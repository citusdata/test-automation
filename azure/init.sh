#!/bin/bash

curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
sudo python get-pip.py

sudo yum install -y \
    git 

echo 'pguser     ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

sudo su pguser       

echo 'export PATH=${HOME}/pg-latest/bin/:$PATH' >> ${HOME}/.bash_profile
echo 'export PATH=${HOME}/.local/bin/:$PATH' >> ${HOME}/.bash_profile

git clone https://github.com/citusdata/test-automation.git

ln -s ${HOME}/test-automation/fabfile ${HOME}/fabfile

echo 'source ${HOME}/test-automation/cloudformation/fab' >> ${HOME}/.bash_profile

pip install -r ${HOME}/test-automation/fabfile/requirements.txt --user

echo | ssh-keygen -P '' -t rsa
cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

