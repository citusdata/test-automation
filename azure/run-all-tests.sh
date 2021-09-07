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

# If running valgrind tests, do not run cleanup function
# This is because, as valgrind tests requires too much time to run,
# we start valgrind tests via nohup in ci. Hence ssh session 
# will immediately be closed just after the fabric command is run
#
# We have a seperate job to terminate the machine and push the results
if [[ $rg_name =~ citusbot_valgrind_.+_test_resource_group ]]; then
    fab_run_cmd_name=''
    if [ "$rg_name" = "citusbot_valgrind_multi_test_resource_group" ]; then
        fab_run_cmd_name="valgrind:check-multi-vg"
    elif [ "$rg_name" = "citusbot_valgrind_multi_1_test_resource_group" ]; then
        fab_run_cmd_name="valgrind:check-multi-1-vg"
    elif [ "$rg_name" = "citusbot_valgrind_columnar_test_resource_group" ]; then
        fab_run_cmd_name="valgrind:check-columnar-vg"
    else
        echo "unexpected valgrind resource group name"
        exit 1
    fi

    nohup fab use.postgres:14.2 use.enterprise:enterprise-master run.$fab_run_cmd_name > /dev/null 2>&1 &

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
