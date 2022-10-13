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

echo "github.com ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ==" >> ~/.ssh/known_hosts

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
