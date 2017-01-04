# test-automation

Tools for making our tests easier to run. Automates setting up a cluster with
CloudFormation and installs a script which automates setting up citus and everything
required for testing citus.

# Starting a cluster

You'll need to have installed the [AWS CLI](https://aws.amazon.com/cli/). Once that's
installed you can run something like:

`cloudformation/create-stack.sh -k [your keypair name] -s MyStack -a eu-central-1a`

This will take some time (around 7 minutes) and emit some instructions for connecting to
the master node.

The name you pass `-s` must be unique. There are more parameters you can pass such as
`-n`, which changes the number of worker nodes which are launched. If you run
`create-stack` with no parameters it will tell you more.

# Connecting to the master

The script should have given you a connection string to use. You can also find the
hostname of the master node in the cloudformation control panel in the "outputs" section.

You'll connect using a string like: `ssh -A ec2-user@ec2-35-156-235-11.eu-central-1.compute.amazonaws.com`.

The "-A" is NOT optional. It is required in order for the master node to be able to ssh
into the worker nodes and for the nodes to be able to checkout private repos. In
addition, your ssh-agent should have the key loaded. That means you should not pass the
`-i` flag into ssh. Instead, run `ssh-add [your pem file]` before
running ssh.

This is an unfortunate restriction which will hopefully be lifted in the future.

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
