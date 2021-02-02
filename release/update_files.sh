#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

## VARIABLES ##
new_branch1=enterprise-master
new_branch2=release-9.5
new_pg_version=13.1
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
