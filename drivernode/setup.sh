
#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

ip_address=$1
rg_name=$2

driverdir="${0%/*}"
cd ${driverdir}

hammerdb_dir=${HOME}/HammerDB-3.3

sed -i "s/replace_with_ip_address/${ip_address}/g" build.tcl
sed -i "s/replace_with_ip_address/${ip_address}/g" run.tcl

cp build.tcl ${hammerdb_dir}/
cp run.tcl ${hammerdb_dir}/

cd ${hammerdb_dir}/src/postgresql
# comment out create database and user as citus cannot do that
sed -i 's/CreateUserDatabase $lda $db $superuser $user $password/#CreateUserDatabase $lda $db $superuser $user $password/g' pgoltp.tcl

sudo yum -y install https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm
sudo yum-config-manager --disable pgdg95
sudo yum -y install postgresql12-server postgresql12

cd ${hammerdb_dir}

mkdir -p results

# build hammerdb related tables
./hammerdbcli auto build.tcl | tee -a ./results/build.log
# run hammerdb benchmark
./hammerdbcli auto run.tcl | tee -a ./results/run.log

cp build.tcl ./results
cp run.tcl ./results

cd $HOME

# add github to known hosts
echo "github.com ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ==" >> ~/.ssh/known_hosts

git clone git@github.com:citusdata/release-test-results.git

git config --global user.email "citus-bot@microsoft.com" 
git config --global user.name "citus bot" 

now=$(date +"%m_%d_%Y_%s")

mv ${hammerdb_dir}/results ${HOME}/release-test-results/hammerdb/${now}

cd ${HOME}/release-test-results

git checkout -b ${rg_name}/${now}
git add -A 
git commit -m "add test results for hammerdb tests ${rg_name}"
git push origin ${rg_name}/${now}