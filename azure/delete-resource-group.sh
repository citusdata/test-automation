#!/bin/bash

echo "waiting a long time to delete resource group, this might take up to 30 mins depending on your cluster size"
az group delete -n ${RESOURCE_GROUP_NAME}
