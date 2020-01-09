#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

coordinator_ip_address=$1
file_name=$2

CH_THREAD_COUNT=1
RAMPUP_TIME=3

cd ${HOME}/HammerDB-3.3

# drop tables if they exist since we might be running hammerdb multiple times with different configs
psql -v "ON_ERROR_STOP=1" -h ${coordinator_ip_address} -f drop-tables.sql

# create ch-benchmark tables in cluster
psql -v "ON_ERROR_STOP=1" -h ${coordinator_ip_address} -f ch-benchmark-tables.sql

# distribute ch-benchmark tables
psql -v "ON_ERROR_STOP=1" -h ${coordinator_ip_address} -f ch-benchmark-distribute.sql

# build hammerdb related tables
./hammerdbcli auto build.tcl | tee -a ./results/build_${file_name}.log

# distribute tpcc tables in cluster
# psql -h ${coordinator_ip_address} -f tpcc-distribute.sql

# distribute functions in cluster 
psql -v "ON_ERROR_STOP=1" -h ${coordinator_ip_address} -f tpcc-distribute-funcs.sql

psql -v "ON_ERROR_STOP=1" -h ${coordinator_ip_address} -f vacuum-ch.sql
psql -v "ON_ERROR_STOP=1" -h ${coordinator_ip_address} -f vacuum-tpcc.sql

./ch_benchmark.py ${CH_THREAD_COUNT} ${coordinator_ip_address} ${RAMPUP_TIME} >> results/ch_benchmarks.log &
ch_pid=$!
echo ${ch_pid}

# run hammerdb benchmark
./hammerdbcli auto run.tcl | tee -a ./results/run_${file_name}.log

kill ${ch_pid}

sleep 30