#!/bin/bash -e

set -euo pipefail

stack_creating=
master_hostname=

function finish {
    if [ -n "${stack_creating}" ]; then
        # Print error messages if any
        echo >&2
        aws cloudformation describe-stack-events \
            --stack-name ${stack_name} \
            --query "StackEvents[?ResourceStatus==\`CREATE_FAILED\`].ResourceStatusReason" \
            --output text

        echo >&2
        echo Deleting stack ${stack_name} >&2
        aws cloudformation delete-stack --stack-name "${stack_name}"
    elif [ -n "${master_hostname}" ]; then

        cat << E_O_MESSAGE

Make sure you've enabled your SSH agent:
 eval \`ssh-agent -s\`
 ssh-add ~/.ssh/id_rsa
 ssh-add [path-to-your-ec2-keypair]

To connect to the master node with SSH agent forwarding:
 ssh -A ec2-user@${master_hostname}

Once you're done, you can delete your stack using:
 aws cloudformation delete-stack --stack-name "${stack_name}"
E_O_MESSAGE

    fi
}

trap finish EXIT

default_cloudformation_template=$(find . -name citus.json | head -n 1)

# outputs usage message on specified device before exiting with provided status
usage() {
	cat << 'E_O_USAGE'
usage: create-stack.sh [-k EC2 key pair] [-p private key file]
                       [-c cloudformation template] [-a availability zone]
                       [-i instance type] [-n number of workers]
                       [-s stack name]

  k : specifies the name of the EC2 key pair to use
      Required.
  p : specifies the private key file to automatically connect and run fab basic-testing on the master
      Optional.
  c : specifies the path to the CloudFormation template
      Default: ${default_cloudformation_template}
  a : specifies the availability zone to use
      Default: us-east-1b
  i : specifies the instance type to use
      Default: c3.xlarge
  n : specifies the number of workers to start
      Default: 2
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
    "--private-key-file") set -- "$@" "-p" ;;
    "--cloudformation-template") set -- "$@" "-c" ;;
    "--availability-zone") set -- "$@" "-a" ;;
    "--instance-type") set -- "$@" "-i" ;;
    "--num-workers") set -- "$@" "-n" ;;
    "--stack-name") set -- "$@" "-s" ;;
    *)        set -- "$@" "$arg"
  esac
done

# Default behavior
key_pair=
private_key_file=
cloudformation_template=${default_cloudformation_template}
availability_zone=us-east-1b
instance_type=c3.xlarge
num_workers=2
stack_name=

# Parse short options
OPTIND=1
while getopts "h:k:i:n:a:s:p:c:" opt
do
  case "$opt" in
    "h") print_usage; exit 0 ;;
    "k") key_pair=${OPTARG} ;;
    "p") private_key_file=${OPTARG} ;;
    "c") cloudformation_template=${OPTARG} ;;
    "a") availability_zone=${OPTARG} ;;
    "i") instance_type=${OPTARG} ;;
    "n") num_workers=${OPTARG} ;;
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

if [ ! -s "${cloudformation_template}" ]; then
    echo Cannot find the CloudFormation template file: "${cloudformation_template}" >&2
    exit 2
fi

if [ ! -z "${private_key_file}" ] && [ ! -s "${private_key_file}" ]; then
    echo Cannot find the private key file: "${private_key_file}" >&2
    exit 3
fi

export AWS_DEFAULT_REGION=${availability_zone:0:${#availability_zone}-1}

echo Creating stack with name ${stack_name} in ${AWS_DEFAULT_REGION}:

aws cloudformation create-stack \
    --output text \
    --template-body "$(cat ${cloudformation_template})" \
    --stack-name "${stack_name}" \
    --on-failure DO_NOTHING \
    --parameters \
        "ParameterKey=KeyName,ParameterValue=${key_pair}" \
        "ParameterKey=AvailabilityZone,ParameterValue=${availability_zone}" \
        "ParameterKey=InstanceType,ParameterValue=${instance_type}" \
        "ParameterKey=NumWorkers,ParameterValue=${num_workers}" \
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

if [ -n "${private_key_file}" ]; then
    echo
    echo Running fab basic-testing on ${master_hostname}
    eval `ssh-agent -s`
    ssh-add ${private_key_file}
    ssh -A ec2-user@${master_hostname} fab --hide stdout
fi
