#!/bin/bash

echo 'export PATH=${HOME}/pg-latest/bin/:$PATH' >> ${HOME}/.bashrc

git clone https://github.com/citusdata/test-automation.git

ln -s ${HOME}/test-automation/fabfile ${HOME}/fabfile

echo 'source ${HOME}/test-automation/cloudformation/fab' >> ${HOME}/.bashrc
echo 'pguser     ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers 

sudo apt-get update && sudo apt install -y \
    python-pip \
    yum

pip install -r ${HOME}/test-automation/fabfile/requirements.txt

