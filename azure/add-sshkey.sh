#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e

eval `ssh-agent -s`
ssh-add ~/.ssh/id_rsa_*

ssh-keygen -y -f ~/.ssh/id_rsa_555bdb88e2e40087bc55c2115267d90d > ~/.ssh/id_rsa.pub
