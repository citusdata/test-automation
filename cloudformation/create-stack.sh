#!/bin/bash -e

set -euo pipefail

stack_creating=

function finish {
    if [ -n "${stack_creating}" ]; then
        cat >&2 << E_O_WARNING
Warning: Your stack is still being created.

To delete your stack, run:
 aws cloudformation delete-stack --stack-name "${stack_name}"
E_O_WARNING
    fi
}

trap finish EXIT

# outputs usage message on specified device before exiting with provided status
usage() {
	cat << 'E_O_USAGE'
usage: create-stack.sh [-k EC2 key pair] [-i instance type]
	[-n number of workers] [-a availability zone]

  k : specifies the name of the EC2 key pair to use
      Required.
  i : specifies the instance type to use
      Default: m3.medium
  n : specifies the number of workers to start
      Default: 2
  a : specifies the availability zone to use
      Default: us-east-1b
  s : specifies the name of the stack
      Default: $USER

create-stack.sh creates a new CloudFormation stack for testing Citus
and returns the hostname of the master.
E_O_USAGE
}

# Transform long options to short ones
for arg in "$@"; do
  shift
  case "$arg" in
    "--help") set -- "$@" "-h" ;;
    "--key-pair") set -- "$@" "-k" ;;
    "--instance-type") set -- "$@" "-i" ;;
    "--num-workers") set -- "$@" "-n" ;;
    "--availability-zone") set -- "$@" "-a" ;;
    "--stack-name") set -- "$@" "-s" ;;
    *)        set -- "$@" "$arg"
  esac
done

# Default behavior
key_pair=
instance_type=m3.medium
num_workers=2
availability_zone=us-east-1c
stack_name=

# Parse short options
OPTIND=1
while getopts "h:k:i:n:a:s:" opt
do
  case "$opt" in
    "h") print_usage; exit 0 ;;
    "k") key_pair=${OPTARG} ;;
    "i") instance_type=${OPTARG} ;;
    "n") num_workers=${OPTARG} ;;
    "a") availability_zone=${OPTARG} ;;
    "s") stack_name=${OPTARG} ;;
    "?") usage >&2; exit 1 ;;
  esac
done
shift $(expr ${OPTIND} - 1)

if [ -z "${key_pair}" ]; then
    echo Specifying a key pair is required >&2
	usage >&2; exit 12; exit 1;
fi

if [ -z "${stack_name}" ]; then
	stack_name=${USER}
fi

export AWS_DEFAULT_REGION=${availability_zone:0:${#availability_zone}-1}

echo Creating stack with name ${stack_name} in ${AWS_DEFAULT_REGION}:

aws cloudformation create-stack \
    --output text \
    --template-body "$(cat citus.json)" \
    --stack-name "${stack_name}" \
    --on-failure DO_NOTHING \
    --parameters \
        "ParameterKey=KeyName,ParameterValue=${key_pair}" \
        "ParameterKey=AvailabilityZone,ParameterValue=${availability_zone}" \
        "ParameterKey=InstanceType,ParameterValue=${instance_type}" \
    --capabilities=CAPABILITY_IAM

stack_creating=1

echo
echo Waiting a long time for stack creation to finish.

start_time=$(date +%s)

aws cloudformation wait stack-create-complete \
    --stack-name "${stack_name}"

end_time=$(date +%s)
stack_creating=

echo
echo Stack creation completed after $((end_time - start_time)) seconds.

master_hostname=$(aws cloudformation describe-stacks \
    --stack-name "${stack_name}" \
    --query 'Stacks[0].Outputs[?OutputKey==`MasterHostname`].OutputValue' \
    --output text)

cat << E_O_MESSAGE

Make sure you've enabled your SSH agent:
 eval \`ssh-agent -s\`
 ssh-add ~/.ssh/id_rsa

To connect to the master node with SSH agent forwarding:
 ssh -A ec2-user@${master_hostname}

Once you're done, you can delete your stack using:
 aws cloudformation delete-stack --stack-name "${stack_name}"
E_O_MESSAGE
