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

hammerdb_version=$(cat ~/HAMMERDB_VERSION)
hammerdb_dir="${HOME}"/HammerDB-"${hammerdb_version}"

cd "${HOME}"
git clone -b test-automation https://github.com/citusdata/ch-benchmark.git
cd ch-benchmark
./generate-hammerdb.sh "$hammerdb_version"
mv HammerDB-"${hammerdb_version}" ~/

# postgres is necessary for hammerdb, so install that
sudo yum -y install https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm
sudo yum-config-manager --disable pgdg95
sudo yum -y install postgresql12-server postgresql12

cd "${driverdir}"

sed -i "s/replace_with_ip_address/${coordinator_ip_address}/g" build.tcl
sed -i "s/replace_with_ip_address/${coordinator_ip_address}/g" run.tcl
sed -i "s/replace_with_username/${username}/g" sql/ch-benchmark-tables.sql

cp build.tcl "${hammerdb_dir}"/
cp run.tcl "${hammerdb_dir}"/
cp ch_benchmark.py "${hammerdb_dir}"/

cp -v ./sql/* "$hammerdb_dir"/

cd "${hammerdb_dir}"

mkdir -p results
