#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# fail in a pipeline if any of the commands fails
set -o pipefail

rg_name=$1

if [ "$rg_name" = "citusbot_pgbench_test_resource_group" ]; then
    fab run.pgbench-tests
    fab run.pgbench-tests --config-file=pgbench_default_without_transaction.ini
fi

if [ "$rg_name" = "citusbot_scale_test_resource_group" ]; then
    fab run.pgbench-tests --config-file=scale_test.ini
fi

if [ "$rg_name" = "citusbot_tpch_test_resource_group" ]; then
    fab run.tpch-automate
fi

if [ "$rg_name" = "citusbot_extension_test_resource_group" ]; then
    fab run.extension-tests
fi

sh "${HOME}"/test-automation/azure/push-results.sh "$1";
