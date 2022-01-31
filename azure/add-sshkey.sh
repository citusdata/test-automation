#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e

eval `ssh-agent -s`
ssh-add ~/.ssh/id_rsa_06b97ddb5954db6d767bf52820fed27d

ssh-keygen -y -f ~/.ssh/id_rsa_06b97ddb5954db6d767bf52820fed27d > ~/.ssh/id_rsa_06b97ddb5954db6d767bf52820fed27d.pub
