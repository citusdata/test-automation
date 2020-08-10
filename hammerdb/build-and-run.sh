#!/bin/bash

# This script is used to start sending transactional and analytical queries.

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

coordinator_ip_address=$1
file_name=$2
is_tpcc=$3
is_ch=$4
username=$5

# a user can specify the ports and password here, which will be used for constructing the
# connection string. As this is not going to be committed anywhere, it should be okay to set
# them here.
password=""
port=5432

# CH_THREAD_COUNT is how many analytical threads will be used.
CH_THREAD_COUNT=1
# tpcc doesn't start recording results while doing a rampup. So we should sleep for that long
# in the analytical script as well so that they start recording around the same time.
RAMPUP_TIME=3
# DEFAULT_CH_RUNTIME_IN_SECS is used when tpcc part is disabled. If tpcc is disabled, this is 
# how long we will run the analytical queries in second.
DEFAULT_CH_RUNTIME_IN_SECS=3600

connection_string=postgres://${username}:${password}@${coordinator_ip_address}:${port}
# you can set the connection string here if you already have it.

export PGUSER=${username}
export PGDATABASE=${username}

hammerdb_version=$(cat ~/HAMMERDB_VERSION)

cd "${HOME}"/HammerDB-"${hammerdb_version}"

# drop tables if they exist since we might be running hammerdb multiple times with different configs
psql -v "ON_ERROR_STOP=1" "${connection_string}" -f drop-tables.sql

# build hammerdb related tables
./hammerdbcli auto build.tcl | tee -a ./results/build_"${file_name}".log

# create ch-benchmark tables in cluster
psql -v "ON_ERROR_STOP=1" "${connection_string}" -f ch-benchmark-tables.sql

# distribute ch-benchmark tables
psql -v "ON_ERROR_STOP=1" "${connection_string}" -f ch-benchmark-distribute.sql

# distribute tpcc tables in cluster
# psql -h ${coordinator_ip_address} -f tpcc-distribute.sql

# distribute functions in cluster 
psql -v "ON_ERROR_STOP=1" "${connection_string}" -f tpcc-distribute-funcs.sql

# do vacuum to get more accurate results.
psql -v "ON_ERROR_STOP=1" "${connection_string}" -f vacuum-ch.sql
psql -v "ON_ERROR_STOP=1" "${connection_string}" -f vacuum-tpcc.sql

# we always do a checkpoint before starting the benchmark so that the timing of it 
# doesn't ruin the results randomly.
psql -v "ON_ERROR_STOP=1" "${connection_string}" -f do-checkpoint.sql

if [ "$is_ch" = true ] ; then
    ./ch_benchmark.py "${CH_THREAD_COUNT}" "${coordinator_ip_address}" "${RAMPUP_TIME}" "${file_name}" >> results/ch_benchmarks.log &
    # store the pid of ch script, we will use this pid to send a kill signal later.
    ch_pid=$!
    echo "${ch_pid}"
fi

if [ "$is_tpcc" = true ] ; then
    # run hammerdb tpcc benchmark
    ./hammerdbcli auto run.tcl | tee -a ./results/run_"${file_name}".log
    # filter and save the NOPM( new orders per minute) to a new file
    grep -oP '[0-9]+(?= NOPM)' ./results/run_"${file_name}".log >> ./results/"${file_name}"_NOPM.log
else
    # if tpcc is not run, we will run the analytical queries for DEFAULT_CH_RUNTIME_IN_SECS seconds.
    sleep "$DEFAULT_CH_RUNTIME_IN_SECS"
fi

# if ch script was being run, we should send it a kill signal so that it will finish
# and log the results.
if [ "$is_ch" = true ] ; then
    kill "${ch_pid}"
    sleep 30
fi

# save the total size of tables, this can be useful for 
psql "${connection_string}" -f tables-total-size.sql >> ./results/table_total_size.out
