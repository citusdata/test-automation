# test-automation

Tools for making our tests easier to run. Automates setting up a cluster with
CloudFormation and installs a script which automates setting up citus and everything
required for testing citus.

# Starting a cluster

You'll need to have installed the [AWS CLI](https://aws.amazon.com/cli/). Once that's
installed you should configure it with `aws configure`. Once it's configured you can run
something like:

`cloudformation/create-stack.sh -k [your keypair name] -s MyStack -a eu-central-1a`

This will take some time (around 7 minutes) and emit some instructions for connecting to
the master node.

The name you pass `-s` must be unique. There are more parameters you can pass such as
`-n`, which changes the number of worker nodes which are launched. If you run
`create-stack` with no parameters it will tell you more.

If you forget the name of your cluster you can get the list of active clusters by running:
`aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE CREATE_IN_PROGRESS CREATE_FAILED --query "StackSummaries[*].{StackName:StackName,StackStatus:StackStatus}"`.
This will only list clusters which are in your default region. You can specify a region
with the `--region` flag.

To get the host of the master you can run: `aws cloudformation describe-stacks --stack-name CS3 --query Stacks[0].Outputs[0].OutputValue`.

# Connecting to the master

1. **Make sure you have a running ssh-agent**

   If you are running linux you either have a running ssh-agent or know that you don't ;). If you're using OSX you probably have a working ssh-agent but it's possible Apple has pushed an update and broken things.

   If it is running then the `SSH_AUTH_SOCK` environment variable will be set:

   ```
   brian@rhythm:~$ echo $SSH_AUTH_SOCK
   /tmp/ssh-s1OzC5ULhRKg/agent.1285
   ```

   If your `SSH_AUTH_SOCK` is empty then Google is your friend for getting an ssh-agent to start automatically when you login. A temporary fix is to run one in the current shell with `exec ssh-agent bash`. This will not appear to have any effect but after you run it `SSH_AUTH_SOCK` should be populated.

2. **Add your private key to your ssh agent**

   When you created your EC2 keypair it gave you a `.pem` file for safekeeping. Add it to your agent with:

   ```
   brian@rhythm:~$ ssh-add Downloads/brian-eu.pem
   Identity added: Downloads/brian-eu.pem (Downloads/brian-eu.pem)
   ```

   Running `ssh-add` or `ssh-add ~/.ssh/id_rsa` will not work, you must use the keypair your received from EC2. `find ~ -name '*.pem'` can help you find it.

3. **ssh into the master in a way which allows it to use your local ssh-agent**

   The `create-stack.sh` script should have given you a connection string to use. You can also find the hostname of the master node in the cloudformation control panel in the "outputs" section.

   You'll connect using a string like:

   ```
   ssh -A ec2-user@ec2-35-156-235-11.eu-central-1.compute.amazonaws.com`.
   ```

   The "-A" is NOT optional. It is required in order for the master node to be able to ssh into the worker nodes and for the nodes to be able to checkout private repos.

   That means you should not pass the `-i` flag into ssh:

   ```
   # careful, this is wrong!
   ssh -i Downloads/brian2.pem ec2-user@[hostname]
   ```

   If you need to pass the `-i` flag in order to connect this means the key is not in your agent. That means the master node will not be able to ssh into the worker nodes when you later run `fab`.

It's unfortunate that you have no flexibility here. This restriction which will hopefully be lifted in the future.

# Example fab commands

Once you have a cluster you can use many different variations of the "fab" command to
install Citus. Here are some examples:

- `fab --list` will return a list of the tasks you can run.
- `fab setup.basic_testing`, will create a vanilla cluster with postgres and citus. Once this has run you can simply run `psql` to connect to it.
- `fab use.citus:v6.0.1 setup.basic_testing` will do the same, but use the tag `v6.0.1` when installing Citus. You can give it any git ref, it defaults to `master`.
- `fab use.postgres:9.6.1 setup.basic_testing` lets you choose your postgres version.
- `fab use.citus:v6.0.1 setup.enterprise` will install postgres and the `v6.0.1` tag of the enterprise repo.

# Ordering of fab tasks

Order is important though! There are three kinds of tasks, `use`, `setup`, and `add`. The
`use` tasks don't take any actions, they just change some configuration which later tasks
use. So, running `fab use.citus:v6.0.1` will do nothing. The `setup` tasks, such as
`setup.enterprise` actually build and install things.

Running `fab setup.enterprise use.citus:v6.0.1` is also a bad idea. The tasks are executed
in order so this will first setup the `enteprise-master` branch of enterprise (because
that's the default) then get ready to use the `v6.0.1` ref then exit.

Finally, there are `add` tasks, such as `add.tpch`. These assume that a cluster is already
installe and running (and therefore must come after the `setup` tasks, and install
additional components, such as the tpch data.

# `add` tasks

It is possible to add extra extensions and features to a Citus cluster:

- `fab add.tpch:scale_factor=1` will generate and stage tpch tables (the default scale factor is 10)
- `fab add.session_analytics` will build and install the session_analytics package (it uses your ssh agent forwarding when connecting to github, so you must have the key you use for github added to your local agent)

There's no need to run these as a separate command.

- `fab use.citus:v6.0.1 setup.enterprise add.shard_rebalancer` does what you'd expect.

# Advanced fab usage

By default your fab commands configure the entire cluster, however they can be targeted
at roles or individual machines.

- `fab -R master pg.restart` will restart postgres on the master node
- `fab -R workers pg.stop` will shutdown pg on all the workers.

You can also ask to run arbitrary commands by adding them after `--`.

- `fab -H 10.0.1.240 -- cat "max_prepared_transactions=0" >> pg-latest/data/postgresql.conf` will modify the postgresql.conf file on the specified worker.
