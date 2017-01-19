#!/bin/sh -e

if [ -z "$AWS_DEFAULT_REGION" ]; then
    export AWS_DEFAULT_REGION=$(curl -s http://169.254.169.254/latest/dynamic/instance-identity/document | grep region | awk -F\" '{print $4}')
fi  

if [ -z "$WORKER_AS_GROUP" ]; then
    WORKER_AS_GROUP=$(cat $HOME/worker-as-group.txt)
fi

AS_GROUP_FILE=/home/ec2-user/group-file
AS_INSTANCES_FILE=/home/ec2-user/worker-instances

aws autoscaling describe-auto-scaling-groups --auto-scaling-group-name $WORKER_AS_GROUP --output text > $AS_GROUP_FILE
INSTANCES=$(grep ^INSTANCES $AS_GROUP_FILE | awk '{print $4}')

if [ "$INSTANCES" != "" ]; then
    aws ec2 describe-instances --instance-ids $INSTANCES --output text | grep PRIVATEIPADDRESSES | cut -f4 > $AS_INSTANCES_FILE
fi
