#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

coordinator_private_ip=$1
driver_private_ip=$2
branch_name=$3

${HOME}/test-automation/hammerdb/setup.sh ${coordinator_private_ip} ${branch_name}
for config_file in "${HOME}/test-automation/fabfile/hammerdb_confs"/*
do
  # get the file name from absolute path 
  config_file=`basename $config_file`

  ssh -o "StrictHostKeyChecking no" -A ${coordinator_private_ip} "source ~/.bash_profile;fab setup.hammerdb:${config_file},driver_ip=${driver_private_ip}"
  ${HOME}/test-automation/hammerdb/build-and-run.sh ${coordinator_private_ip} ${config_file}
done

${HOME}/test-automation/hammerdb/upload-results.sh ${branch_name}