#!/bin/bash

az group deployment create -g $1 --template-file azuredeploy.json --parameters azuredeploy.parameters.json --debug
