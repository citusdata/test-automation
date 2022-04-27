#!/bin/bash

# fail if trying to reference a variable that is not set.
set -u
# exit immediately if a command fails
set -e

eval `ssh-agent -s`

# Circle CI's specification has a list of certificates to
# add to the job. The keys are added like id_rsa_FINGERPRINT
# this line loads them all to the ssh-agent for later use

ssh-add ~/.ssh/id_rsa_*

