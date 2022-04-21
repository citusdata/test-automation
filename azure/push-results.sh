#!/bin/bash

# this scripts pushes the results under results/ directory to release-test-results repository

# args #
# $1 -> branch name to push results

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# fail in a pipeline if any of the commands fails
set -o pipefail

branch_name=$1

# add github to known hosts

ssh-keyscan -H github.com >> ~/.ssh/known_hosts

ssh-add -l
ls ~/.ssh/

git clone git@github.com:citusdata/release-test-results.git "${HOME}"/release-test-results

git config --global user.email "citus-bot@microsoft.com" 
git config --global user.name "citus bot" 

now=$(date +"%m_%d_%Y_%s")

mv "${HOME}"/results "${HOME}"/release-test-results/periodic_job_results/"${now}"

cd "${HOME}"/release-test-results

commit_message="add test results"

git checkout -b "${branch_name}/${now}"
git add -A 
git commit -m "$commit_message"
git push origin "${branch_name}/${now}"
