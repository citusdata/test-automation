#!/bin/bash

rg=$1

az group create -l eastus -n ${rg}

az group deployment create -g ${rg} --template-file azuredeploy.json --parameters azuredeploy.parameters.json --debug
