resource_group=$1

az group deployment create -g ${resource_group} --template-file resource_gp_cleanup.json --mode complete
