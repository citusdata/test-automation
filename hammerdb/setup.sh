
#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

coordinator_ip_address=$1
rg_name=$2

driverdir="${0%/*}"
cd ${driverdir}

hammerdb_dir=${HOME}/HammerDB-3.3

sed -i "s/replace_with_ip_address/${coordinator_ip_address}/g" build.tcl
sed -i "s/replace_with_ip_address/${coordinator_ip_address}/g" run.tcl

cp build.tcl ${hammerdb_dir}/
cp run.tcl ${hammerdb_dir}/
cp tpcc-distribute.sql ${hammerdb_dir}/ 
cp tpcc-distribute-funcs.sql ${hammerdb_dir}/
cp drop-tables.sql ${hammerdb_dir}/ 

# cd ${HOME}
# git clone --branch citus https://github.com/SaitTalhaNisanci/HammerDB.git
# mv HammerDB/src/postgresql/pgoltp.tcl HammerDB-3.3/src/postgresql/pgoltp.tcl

cd ${hammerdb_dir}/src/postgresql
comment out create database and user as citus cannot do that
sed -i 's/CreateUserDatabase $lda $db $superuser $user $password/#CreateUserDatabase $lda $db $superuser $user $password/g' pgoltp.tcl

sudo yum -y install https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm
sudo yum-config-manager --disable pgdg95
sudo yum -y install postgresql12-server postgresql12

cd ${hammerdb_dir}

mkdir -p results
