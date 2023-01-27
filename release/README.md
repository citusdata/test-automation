
# Usage of update_files.sh

If you will test a custom branch, you can update all the config files with `./update_files.sh`. Say that you 
will do the release testing for `release-11.1` and `main`. You can do the following:

```bash
vim update_files.sh

new_branch1=release-11.1
new_branch2=main
new_pg_version=15.1

./update_files.sh # this will update all the branches correctly
git diff #make sure that everything is fine
```
