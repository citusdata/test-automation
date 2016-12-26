#!/bin/bash

aws cloudformation create-stack --template-body "$(cat citus.json)" --stack-name Test2 --parameters ParameterKey=KeyName,ParameterValue=brian-eu ParameterKey=AvailabilityZone,ParameterValue=eu-central-1a ParameterKey=InstanceType,ParameterValue=t2.medium --capabilities=CAPABILITY_IAM
