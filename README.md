# test-automation
Tools for making our tests easier to run

# Connecting to the master

Once you have spun up a stack you'll want to ssh into it! You can find the hostname (something like `ec2-35-156-235-11.eu-central-1.compute.amazonaws.com` in the "outputs" section of the cloudformation panel. Connect to the node using a command string like: `ssh -A ec2-user@ec2-35-156-235-11.eu-central-1.compute.amazonaws.com`.

The "-A" is NOT optional. It is required in order for the master node to be able to ssh into the worker nodes. In addition, your ssh-agent should have your key loaded. That means you should not pass the `-i` flag into ssh. Instead, run `ssh-add [your pem file]` before running ssh.

This is an unfortunate restriction which will hopefully be lifted in the future.

# Running fab

- `fab basic_testing` will setup a vanilla cluster with postgres and citus for you to play with
- `fab citus:v6.0.1 basic_testing` (you can give it any git ref) is how you override the default branch (master) which fab uses.
- `fab --list` will return a list of the tasks you can run.
