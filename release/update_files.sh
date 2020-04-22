#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e
# echo commands
set -x

## VARIABLES ##

old_branch1=enterprise-master # this will be replaced with new_branch1
old_branch2=release-9.2 # this will be replaced with new_branch2

new_branch1=release-9.3
new_branch2=release-9.2

old_pg_version=12.1 # this will be replaced with new_pg_version
new_pg_version=12.2
## VARIABLES ##

releasedir="${0%/*}"
cd ${releasedir}/.. # topdir

dummy_intermediate_branch1=dummy_intermediate_branch1
dummy_intermediate_branch2=dummy_intermediate_branch2

# first we replace the old branches to some unique dummy value so that 
# we prevent any wrong placements. For example if the old branches were release-9.3 and release-9.2
# if we replaced them with release-9.4 and release-9.3, depending on the ordering of replacement, 
# we could end with with all branches being release-9.4.
find . -type f -name "*.ini" | xargs sed -i "s@${old_branch1}@${dummy_intermediate_branch1}@g"
find . -type f -name "*.ini" | xargs sed -i "s@${old_branch2}@${dummy_intermediate_branch2}@g"

find . -type f -name "*.ini" | xargs sed -i "s@${dummy_intermediate_branch1}@${new_branch1}@g"
find . -type f -name "*.ini" | xargs sed -i "s@${dummy_intermediate_branch2}@${new_branch2}@g"

# replace pg versions
find . -type f -name "*.ini" | xargs sed -i "s@${old_pg_version}@${new_pg_version}@g"
