#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

coordinator_ip_address=$1
username=$2

driverdir="${0%/*}"
cd "${driverdir}"

hammerdb_dir="${HOME}"/HammerDB-3.3

sed -i "s/replace_with_ip_address/${coordinator_ip_address}/g" build.tcl
sed -i "s/replace_with_ip_address/${coordinator_ip_address}/g" run.tcl
sed -i "s/replace_with_username/${username}/g" sql/ch-benchmark-tables.sql

cp build.tcl "${hammerdb_dir}"/
cp run.tcl "${hammerdb_dir}"/
cp ch_benchmark.py "${hammerdb_dir}"/

cp -v ./sql/* "$hammerdb_dir"/

cd "${HOME}"

wget "https://github.com/TPC-Council/HammerDB/releases/download/v3.3/HammerDB-3.3-Linux.tar.gz"
tar -zxvf HammerDB-3.3-Linux.tar.gz

# here we use our fork, because it distributed tables at the beginning, which speeds up the process
# since we can create indexes in parallel etc.
git clone --branch citus https://github.com/SaitTalhaNisanci/HammerDB.git
mv HammerDB/src/postgresql/pgoltp.tcl "${hammerdb_dir}"/src/postgresql/pgoltp.tcl

# cd ${hammerdb_dir}/src/postgresql
# comment out create database and user as citus cannot do that
# sed -i 's/CreateUserDatabase $lda $db $superuser $user $password/#CreateUserDatabase $lda $db $superuser $user $password/g' pgoltp.tcl

# postgres is necessary for hammerdb, so install that
sudo yum -y install https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm
sudo yum-config-manager --disable pgdg95
sudo yum -y install postgresql12-server postgresql12

cd "${hammerdb_dir}"

mkdir -p results
