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
    # fab run.pgbench_tests:pgbench_default_without_transaction.ini
fi 

if [ "$rg_name" = "citusbot_scale_test_resource_group" ]; then
    fab run.pgbench_tests:scale_test.ini
fi

if [ "$rg_name" = "citusbot_tpch_test_resource_group" ]; then
    fab run.tpch_automate
fi 

# If running valgrind tests, do not run cleanup function
# This is because, as valgrind tests requires too much time to run,
# we start valgrind tests via nohup in ci. Hence ssh session 
# will immediately be closed just after the fabric command is run
#
# We have a seperate job to terminate the machine and push the results
if [ "$rg_name" = "citusbot_valgrind_test_resource_group" ]; then
    nohup fab use.postgres:13.1 use.enterprise:enterprise-master run.valgrind > /dev/null 2>&1 &

    # wait for cloning to end
    while ! test -d "$HOME/citus-enterprise";
    do
        echo "Wait until citus is cloned completely ...";
        sleep 60;
    done

    echo "Citus is cloned succesfully";
else
    sh "${HOME}"/test-automation/azure/push-results.sh "$1";
fi 
