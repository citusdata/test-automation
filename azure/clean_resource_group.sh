#!/bin/bash

resource_group=$1

az group delete -n ${resource_group}
