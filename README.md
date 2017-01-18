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

To get the hostname of the master you can run: `aws cloudformation describe-stacks --stack-name CS3 --query Stacks[0].Outputs[0].OutputValue`.

# Connecting to the master

1. **Make sure you have a running ssh-agent**

   If you are running linux you either have a running ssh-agent or know that you don't ;).
   If you're using OSX you probably have a working ssh-agent but it's possible Apple has
   pushed an update and broken things.

   If it is running then the `SSH_AUTH_SOCK` environment variable will be set:

   ```bash
   brian@rhythm:~$ echo $SSH_AUTH_SOCK
   /tmp/ssh-s1OzC5ULhRKg/agent.1285
   ```

   If your `SSH_AUTH_SOCK` is empty then Google is your friend for getting an ssh-agent to
   start automatically when you login. As a temporary fix you can run `exec ssh-agent bash`:

   ```bash
   brian@rhythm:~$ echo $SSH_AUTH_SOCK

   brian@rhythm:~$ exec ssh-agent bash
   brian@rhythm:~$ echo $SSH_AUTH_SOCK
   /tmp/ssh-et5hwGiqPxUn/agent.31580
   ```

2. **Add your keypair's private key to your ssh agent**

   When you created your EC2 keypair it gave you a `.pem` file for safekeeping. Add it to
   your agent with:

   ```bash
   brian@rhythm:~$ ssh-add Downloads/brian-eu.pem
   Identity added: Downloads/brian-eu.pem (Downloads/brian-eu.pem)
   ```

   `find ~ -name '*.pem'` can help you find your key. Running `ssh-add ~/.ssh/id_rsa` will
   not work, you must use the keypair you received from EC2.

3. **If you plan on checking out private repos, add that private key to your agent as well**

   When you check out a private repo on the master/workers, they will reach back and talk
   to your ssh-agent in order to authenticate as you when talking to Github. You can find
   your list of keys [here](https://github.com/settings/keys). One of them should be added
   to ssh-agent with another `ssh-add` command. Personally, I run:

   ```
   brian@rhythm:~$ ssh-add
   Identity added: /home/brian/.ssh/id_rsa (/home/brian/.ssh/id_rsa)
   ```

   Note: If you use 2-factor authentication that will not change these instructions in any
   way. For the purposes of ssh access your key counts as a factor. If you have a
   passphrase on your key you will be prompted for it when you run `ssh-add`, that's the
   second factor. If you do not have a passphrase on your key, well, Github has no way of
   knowing that.

4. **ssh into the master in a way which allows it to use your local ssh-agent**

   The `create-stack.sh` script should have given you a connection string to use. You can
   also find the hostname of the master node in the cloudformation control panel in the
   "outputs" section. There's a command above which tells you how to get the hostname
   without going to the control panel.

   You'll connect using a string like:

   ```bash
   ssh -A ec2-user@ec2-35-156-235-11.eu-central-1.compute.amazonaws.com
   ```

   The `-A` is not optional. It is required so the master node can ssh into the worker
   nodes and so the nodes can checkout private repos.

   That means you should not pass the `-i` flag into ssh:

   ```bash
   # careful, this is wrong!
   ssh -i Downloads/brian2.pem ec2-user@[hostname]
   ```

   If you need to pass the `-i` flag in order to connect this means the key is not in your
   agent. That means the master node will not be able to ssh into the worker nodes when you
   later run `fab`.

It's unfortunate that you have no flexibility here. This restriction which will hopefully
be lifted in the future.

# Example fab commands

Use `fab --list` to see all the tasks you can run! This is just a few examples.

Once you have a cluster you can use many different variations of the "fab" command to
install Citus:

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
installed and running, and install additional components, such as the tpch data. Since
they require that you already have a cluster, they must be run after a `setup` task!

# `add` tasks

It is possible to add extra extensions and features to a Citus cluster:

- `fab add.tpch:scale_factor=1` will generate and stage tpch tables (the default scale factor is 10)
- `fab add.session_analytics` will build and install the session_analytics package (see the instructions above for information on how to checkout this private repo)

You can run these at the same time as you run `setup` tasks:

- `fab use.citus:v6.0.1 setup.enterprise add.shard_rebalancer` does what you'd expect.

# Advanced fab usage

By default your fab commands configure the entire cluster, however you can target roles or
individual machines.

- `fab -R master pg.restart` will restart postgres on the master node.
- `fab -R workers pg.stop` will shutdown pg on all the workers.
- `fab -H 10.0.1.240 pg.start` will start pg on that specific node.

You can also ask to run arbitrary commands by adding them after `--`.

- `fab -H 10.0.1.240 -- cat "max_prepared_transactions=0" >> pg-latest/data/postgresql.conf` will modify the postgresql.conf file on the specified worker.
- `fab -- 'cd citus && git checkout master && make install'` to switch the branch of Citus you're using. (This runs on all nodes)

# Using multiple Citus installations, `pg-latest`

Some kinds of tests (such as TPC-H) are easier to perform if you create multiple
simultanious installations of Citus and are able to switch between them. The fabric
scripts allow this by maintaining a symlink called `pg-latest`.

Most tasks which interact with a postgres installation (such as `add.cstore` or `pg.stop`)
simply use the installation in `pg-latest`. Tasks such as `setup.basic_testing` which
install postgres will overwrite whatever is currently in `pg-latest`.

You can change where `pg-latest` points by running `fab set_pg_latest:some-absolute-path`. For
example: `fab set_pg_latest:/home/ec2-user/enterprise-installation`. Using multiple
installations is a matter of changing your prefix whenever you want to act upon or create
a different installation.

Here's an example:

```bash
fab set_pg_latest:/home/ec2-user/pg-960-citus-600
fab use.postgres:9.6.0 use.citus:v6.0.0 setup.basic_testing
fab set_pg_latest:/home/ec2-user/pg-961-citus-601
fab use.postgres:9.6.1 use.citus:v6.0.1 setup.basic_testing
# you now have 2 installations of Citus!
fab pg.stop  # stop the existing Citus instance
fab set_pg_latest:/home/ec2-user/pg-960-citus-600  # switch to using the new instance
fab pg.start  # start the new instance
# now you've switched back to the first installation

# the above can be abbreviated by writing the following:
fab pg.stop set_pg_latest:/home/ec2-user/pg-960-citus-600 pg.start
```
