
# Usage of update_files.sh

If you will test a custom branch, you can update all the config files with `./update_files.sh`. Say that you 
will do the release testing for `release-9.2` and `release-9.3`. You can do the following:

```bash
vim update_files.sh

new_branch1=release-9.3
new_branch2=release-9.2
new_pg_version=12.2

./update_files.sh # this will update all the branches correctly
git diff #make sure that everything is fine
```
