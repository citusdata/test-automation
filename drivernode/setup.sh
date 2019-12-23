
#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

ip_address=$1

driverdir="${0%/*}"
cd ${driverdir}

sed -i "s/replace_with_ip_address/${ip_address}/g" build.tcl
sed -i "s/replace_with_ip_address/${ip_address}/g" run.tcl

cd $HOME
