#!/bin/bash

# https://vaneyckt.io/posts/safer_bash_scripts_with_set_euxo_pipefail/
set -euxo pipefail

source ./utils.sh

script_directory="$(dirname "${BASH_SOURCE[0]}")"
script_directory="$(realpath "${script_directory}")"

project_directory="$script_directory/../.."
project_directory="$(realpath "${project_directory}")"

# the user that will be used to run citus_dev
PG_USER=pguser
useradd $PG_USER

# give ownership of the project directory to the pguser
chown $PG_USER $project_directory

apt-get update

# used to parse the json config
apt-get install -y jq

# download the jdbc driver
jdbc_version=$(cat ./jdbc_config.json | jq '.jdbc_version' | remove_string_quotations)
jdbc_jar_name="postgresql-${jdbc_version}.jar"
wget -O $jdbc_jar_name --no-verbose "https://jdbc.postgresql.org/download/${jdbc_jar_name}"

# download java sdk
apt-get install -y default-jdk

cd $project_directory

# install build dependencies for pg and citus
# based on: https://github.com/citusdata/citus/blob/master/CONTRIBUTING.md#debian-based-linux-ubuntu-debian
apt-get install -y autoconf flex bison libcurl4-gnutls-dev libicu-dev \
                        libkrb5-dev liblz4-dev libpam0g-dev libreadline-dev \
                        libselinux1-dev libssl-dev libxslt1-dev libzstd-dev \
                        uuid-dev

# install pg
pg_version=$(cat $script_directory/jdbc_config.json | jq '.pg_version' | remove_string_quotations)

# declares a PG_BIN_DIR variable and appends it to PATH
install_pg_with_version $pg_version "--with-openssl"

# get the citus repo
citus_branch=$(cat $script_directory/jdbc_config.json | jq '.citus_branch' | remove_string_quotations)
git clone --branch $citus_branch https://oauth2:$RESULT_REPO_ACCESS_TOKEN@github.com/citusdata/citus.git citus

cd citus
echo $PG_BIN_DIR
PG_CONFIG=$PG_BIN_DIR/pg_config ./configure
make -sj $(nproc) install

cd $project_directory

# declares COOR_PORT
create_test_cluster $PG_USER

cd $script_directory
jdbc_driver_path="$script_directory/$jdbc_jar_name"

# print installed citus version first
psql -p $COOR_PORT -U $PG_USER -c "select citus_version();"

# compile java class
javac JDBCReleaseTest.java

cd ../tpch_2_13_0

# build dbgen to generate test data
make clean
make

# generate test data
SCALE_FACTOR=1 CHUNKS="o 24 c 4 P 1 S 4 s 1" sh generate2.sh

cd ..

# perform jdbc tests for combinations of different citus executors & partitioned tables
# ---
# note that "append" has been commented out from the distribution table types since the
# \COPY command for append distributed tables requires a append_to_shard :shardid option
# "append" can be uncommented back if that option is no longer required.
for type in hash #append
do
  for executor in real-time task-tracker adaptive
  do
    cd tpch_2_13_0

    # drop existing tables & create new ones
    psql -p $COOR_PORT -U $PG_USER -f drop_tables.sql -f tpch_create_${type}_partitioned_tables.ddl

    # ingest data
    for tbl in *.tbl.*
      do psql -p $COOR_PORT -U $PG_USER -c "\COPY ${tbl%.tbl.*} FROM '$tbl' WITH DELIMITER '|'"
    done

    cd ..

    echo $executor
    echo $type
    # finally, run jdbc tests for (type x executor) combination
    CLASSPATH=$jdbc_driver_path:jdbc java JDBCReleaseTest $executor $PG_USER $COOR_PORT
  done
done
