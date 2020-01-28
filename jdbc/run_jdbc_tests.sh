#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "Exactly two arguments should be provided"
    echo "Arg1: Provide an available port for the coordinator instance of the temporary citus cluster to perform jdbc tests"
    echo "Arg2: Provide path to jdbc driver for PostgreSQL, (see https://jdbc.postgresql.org/ to download it)"

    exit 1
fi

coordinator_port=$1
jdbc_driver_path=$2

# create & run tmp citus cluster for jdbc test 
citus_dev stop /tmp/jdbc_test_db --port $coordinator_port
rm -rf /tmp/jdbc_test_db
mkdir -p /tmp/jdbc_test_db
citus_dev make /tmp/jdbc_test_db --port $coordinator_port

# print installed citus version first
psql -p $coordinator_port -d $USER -c "select citus_version();"

# compile java class
javac JDBCReleaseTest.java

cd ../tpch_2_13_0

# clean & build dbgen to generate test data
make clean
make

# generate test data
SCALE_FACTOR=1 CHUNKS="o 2 c 2 P 1 S 2 s 1" sh generate2.sh

cd ..

# perform jdbc tests for combinations of different citus executors & partitioned tables
for type in hash append
do
  for executor in real-time task-tracker adaptive
  do
    cd tpch_2_13_0

    # drop existing tables & create new ones
    psql -p $coordinator_port -d $USER -f drop_tables.sql -f tpch_create_${type}_partitioned_tables.ddl

    # ingest data
    for tbl in *.tbl.*
      do psql -p $coordinator_port -d $USER -c "\COPY ${tbl%.tbl.*} FROM '$tbl' WITH DELIMITER '|'"
    done

    cd ..

    # finally, run jdbc tests for (type x executor) combination
    CLASSPATH=$jdbc_driver_path:jdbc java JDBCReleaseTest $executor $USER $coordinator_port > ${type}_${executor}
  done
done
