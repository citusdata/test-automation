#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e

eval `ssh-agent -s`
ssh-add

ssh-keygen -y -f ~/.ssh/id_rsa > ~/.ssh/id_rsa.pub
