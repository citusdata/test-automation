#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

hammerdb_dir=${HOME}/HammerDB-3.3
rg_name=$1

cd ${hammerdb_dir}

cp build.tcl ./results
cp run.tcl ./results

cd $HOME

# add github to known hosts
echo "github.com ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ==" >> ~/.ssh/known_hosts

git clone https://github.com/citusdata/release-test-results.git

git config --global user.email "citus-bot@microsoft.com" 
git config --global user.name "citus bot" 

now=$(date +"%m_%d_%Y_%s")

mv ${hammerdb_dir}/results ${HOME}/release-test-results/hammerdb/${now}

cd ${HOME}/release-test-results

git checkout -b ${rg_name}/${now}
git add -A 
git commit -m "add test results for hammerdb tests ${rg_name}"
git push origin ${rg_name}/${now}