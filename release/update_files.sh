#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

## VARIABLES ##
new_branch1=enterprise-master
new_branch2=release-10.1
new_pg_version=13.4
new_use_enterprise=on
## VARIABLES ##

releasedir="${0%/*}"
cd ${releasedir}/.. # topdir
# replace all .ini config files:
# postgres_citus_versions: [('<pg_version>', '<branch_name>'), ('<pg_version>', '<branch_name2>')]
# postgres_citus_versions: [('<new_pg_version>', '<new_branch1>'), ('<new_pg_version>', '<new_branch2>')]
find . -type f -name "*.ini" |
    xargs sed -i "s@postgres_citus_versions: \[('[^,;]\+', '[^,;]\+'), ('[^,;]\+', '[^,;]\+')\]@postgres_citus_versions: \[('${new_pg_version}', '${new_branch1}'), ('${new_pg_version}', '${new_branch2}')\]@g"
# replace all .ini config files:
# postgres_citus_versions: [('<pg_version>', '<branch_name>')]
# postgres_citus_versions: [('<new_pg_version>', '<new_branch1>')]
find . -type f -name "*.ini" | 
    xargs sed -i "s@postgres_citus_versions: \[('[^,;]\+', '[^,;]\+')\]@postgres_citus_versions: \[('${new_pg_version}', '${new_branch1}')\]@g"
# replace all .ini config files:
# use_enterprise: <use_enterprise>
# use_enterprise: <new_use_enterprise>
find . -type f -name "*.ini" | 
    xargs sed -i "s@use_enterprise: [^,;]\+@use_enterprise: ${new_use_enterprise}@g"
