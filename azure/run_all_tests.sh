#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# fail in a pipeline if any of the commands fails
set -o pipefail

#fab run.pgbench_tests
# mock tests
mkdir ${HOME}/test-automation/results
echo "mocking tests" > ${HOME}/test-automation/results/mock_pgbench_tests.out


git clone git@github.com:citusdata/release-test-results.git

git config --global user.email "citus-bot@microsoft.com" 
git config --global user.name "citus bot" 

now=$(date +"%m_%d_%Y")

mv ${HOME}/test-automation/results ${HOME}/release-test-results/periodic_job_results/${now}

cd ${HOME}/release-test-results

git checkout -b ${now}
git add -A 
git commit -m "add test results for performance tests ${now}"
git push origin ${now}
