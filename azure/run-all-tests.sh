#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# fail in a pipeline if any of the commands fails
set -o pipefail

rg_name=$1

if [ "$rg_name" = "citusbot_pgbench_test_resource_group" ]; then
    fab run.pgbench_tests
    fab run.pgbench_tests:pgbench_default_without_transaction.ini
fi 

if [ "$rg_name" = "citusbot_scale_test_resource_group" ]; then
    fab run.pgbench_tests:scale_test.ini
fi

if [ "$rg_name" = "citusbot_tpch_test_resource_group" ]; then
    fab run.tpch_automate
fi 


# add github to known hosts
echo "github.com ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ==" >> ~/.ssh/known_hosts

git clone git@github.com:citusdata/release-test-results.git

git config --global user.email "citus-bot@microsoft.com" 
git config --global user.name "citus bot" 

now=$(date +"%m_%d_%Y_%s")

mv ${HOME}/results ${HOME}/release-test-results/periodic_job_results/${now}

cd ${HOME}/release-test-results

git checkout -b ${rg_name}/${now}
git add -A 
git commit -m "add test results for performance tests ${rg_name}"
git push origin ${now}
