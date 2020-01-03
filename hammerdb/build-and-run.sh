#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

coordinator_ip_address=$1
file_name=$2

cd ${HOME}/HammerDB-3.3

# drop tables if they exist since we might be running hammerdb multiple times with different configs
psql -h ${coordinator_ip_address} -f drop-tables.sql

# build hammerdb related tables
./hammerdbcli auto build.tcl | tee -a ./results/build_${file_name}.log

# distribute tpcc tables in cluster
psql -h ${coordinator_ip_address} -f tpcc-distribute.sql

# run hammerdb benchmark
./hammerdbcli auto run.tcl | tee -a ./results/run_${file_name}.log
