#!/bin/bash

# https://vaneyckt.io/posts/safer_bash_scripts_with_set_euxo_pipefail/
set -euxo pipefail

source ../azure/add-sshkey.sh
source ./utils.sh

script_directory="$(dirname "${BASH_SOURCE[0]}")"
script_directory="$(realpath "${script_directory}")"

# used to parse the json config
sudo apt-get install -y jq

# download the jdbc driver
jdbc_version=$(cat ./jdbc_config.json | jq '.jdbc_version' | remove_string_quotations)
jdbc_jar_name="postgresql-${jdbc_version}.jar"
wget -O $jdbc_jar_name --no-verbose "https://jdbc.postgresql.org/download/${jdbc_jar_name}"

# download java sdk
sudo apt-get install -y default-jdk

cd $HOME

# install pg
pg_version=$(cat ./jdbc_config.json | jq '.pg_version' | remove_string_quotations)
install_pg_version $pg_version "--with-openssl"

# get the citus repo
citus_branch = $(cat ./jdbc_config.json | jq '.citus_branch' | remove_string_quotations)
use_enterprise = $(cat ./jdbc_config.json | jq '.use_enterprise')

if[ "$use_enterprise" == "true" ]; then
  git clone --branch $citus_branch git@github.com:citusdata/citus-enterprise.git citus
else
  git clone --branch $citus_branch git@github.com:citusdata/citus.git citus
fi

cd citus
./configure
make -sj $(nproc) install

# install citus_dev to setup the cluster
cd ..

jdbc_driver_path="./$jdbc_jar_name"
coordinator_port=9700


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
