# test-automation

Tools for making our tests easier to run. Automates setting up a cluster with
Azure/Cloudformation and installs a script which automates setting up citus and everything
required for testing citus.

## Table of Contents

* [Azure](#azure)
  * [Getting Started](#azure-getting-started)
    * [Setup steps for each test](#azure-setup-steps)
    * [Steps to delete a cluster](#azure-delete-cluster)
  * [Under The Hood](#under-the-hood)  
* [AWS(Deprecated)](#AWS)
  * [Getting Started](#getting-started)
    * [Setup steps for each test](#aws-setup-steps)
    * [Steps to delete a cluster](#aws-delete-cluster)
  * [Detailed Configuration](#detailed-configuration)
    * [Starting a Cluster](#start-a-cluster)
    * [Connecting to the Master](#connect-to-master)
* [Running Rests](#running-tests)
  * [Basic Cluster Setup](#basic-cluster-setup)
  * [Running PgBench Tests](#pgbench)
  * [Running Scale Tests](#scale)
  * [Running PgBench Tests Against Hyperscale (Citus)](#pgbench-cloud)
  * [Running TPC-H Tests](#tpch)
  * [Running TPC-H Tests Against Hyperscale (Citus)](#tpch-cloud)
  * [Running Valgrind Tests](#valgrind)
* [Example fab Commands](#fab-examples)
* [Tasks, and Ordering of Tasks](#fab-tasks)
* [Task Namespaces](#task-namespaces)
  * [`use`, Choose Exactly What to Install](#use)
  * [`add`, Add add-ons (such as extensions) to a Citus Cluster](#add)
  * [`pg`, Run Commands Involving pg_ctl and psql](#pg)
  * [`run`, Run pgbench and tpch Rests Automatically](#run)
* [Advanced fab Usage](#advanced-fab)
  * [Using Multiple Citus Installations](#multiple-installs)

## <a name="azure"></a>Azure

## <a name="azure-getting-started"></a> Getting Started

You can find more information about every step below in other categories. This list of commands show how to get started quickly. Please see other items below to understand details and solve any problems you face.

### Prerequisites
1. You should have `az cli` in your local to continue. [Install instructions](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest)
2. Run `az login` to make the CLI log in to your account
3. Make sure that your default subscription is the right one:
    ```bash
    # List your subscriptions
    az account list
    # Pick the correct one from the list and run
    az account --set subscription {uuid-of-correct-subscription}
    ```

4. You should use `ssh-agent` to add your ssh keys, which will be used for downloading the enterprise repository. Note that your keys are kept only in memory, therefore this is a secure step.
    ```bash
    # start ssh agent
    eval `ssh-agent -s`

    # Add your Github ssh key for enterprise (private) repo
    ssh-add
    ```


### General info
In `azuredeploy.parameters.json` file, you will see the parameters that you can change. For example if you want to change the number of workers, you will need to change the parameter `numberOfWorkers`. You can change the type of coordinator and workers separately from the parameters file. Also by default for workers, memory intense vms are used(E type) while for coordinator CPU intense vms are used(D type).

After you run tests, you can see the results in `results` folder. The `results` folder will have the name of the config used for the test.

The data will be stored on the attached disk, size of which can be configured in the parameters.

If you dont specify the region, a random region among `eastus`, `west us 2` and `south central us` will be chosen. This is to use resources uniformly from different regions.

## <a name="azure-setup-steps"></a> Setup Steps For Each Test

You will need to follow these steps to create a cluster and connect to it, on your local machine:

```bash

# in the session that you will use to ssh, set the resource group name
export RESOURCE_GROUP_NAME=give_your_name_citus_test_automation_r_g

# if you want to configure the region
# export AZURE_REGION=eastus2

# Go to the azure directory to have access to the scripts
cd azure

# open and modify the instance types/discs as you wish
# For valgrind tests, you *need to set* `numberOfWorkers` to `0` as we only need a single machine cluster.
# This is because we will already be using our regression test structure and it creates a local cluster itself.
# Also, as we install `valgrind` only on coordinator, if we have worker nodes, then we cannot build
# PostgreSQL as we require `valgrind` on workers too  and get error even if we do not need them :).
less azuredeploy.parameters.json

# Quickly start a cluster of with defaults. This will create a resource group and use it for the cluster.
./create-cluster.sh

# connect to the coordinator
./connect.sh

# ALTERNATIVATELY instead of ./connect.sh you can do the following

# Delete security rule 103 to be able to connect
./delete-security-rule.sh

# When your cluster is ready, it will prompt you with the connection string, connect to coordinator node
ssh -A pguser@<public ip of coordinator>
```

## <a name="azure-delete-cluster"></a> Steps to delete a cluster

After you are done with testing you can run the following the delete a cluster and the relevant resource group:

```bash
# Delete the formation
# It's a good practice to check deletion status from the azure console
./delete-resource-group.sh
```

<details>
  <summary>Under the hood</summary>

## <a name="under-the-hood"></a>Under The Hood

  Azure has ARM templates that can be used to deploy servers with ease. There are two main files for ARM templates, `azuredeploy.json` and `azuredeploy.parameters.json`. `azuredeploy.json` has the main template and `azuredeploy.parameters.json` contains the parameters that are used in the main template. For example if you want to change the number of workers, you would do that in the parameters. You shouldnt change anything in the template file for configuration.

  The main template has 4 main parts:
  
* Parameters
* Variables
* Resources
* Outputs

Parameters can be configured from the parameters file. Variables are constants. Resources have all of the resource definitions such as VMs, network security groups. Outputs can be useful for displaying a connection string.

When creating resources, we can specify the order so that if a resource depends on some other resource, it wont be created before the dependant is created. We can also specify how many instances of a resource to create with a `copy` command.

The first virtual machine with index 0 is treated as a coordinator. When all the virtual machines are ready, a custom script is installed to do initialization in vms. The initailization script is retrieved from the github with a url.

The initialization script also finds the private ip addresses of workers and puts them to the coordinator. The way this is done is with a storage account resource. This storage account resource is created within the template itself and all the vms upload their private ip addresses to the storage. After all are uploaded the coordinator downloads all the private ip addresses from the storage account and puts it to `worker-instances` file, which is then used when creating a citus cluster.

We have a special security group which blocks ssh traffic. The rule's priority is 103 and 100, 101, 102 are also taken by this security group. The workaround to connect to the coordinator is to remove the rule 103, and connect right after it. The rule comes back in 2-3 mins, so you should be fast here. There is a script called `delete-security-rule.sh`, which deletes that rule for you.

You can use `connect.sh` which will delete the security rule and connect to the coordinator for you.

Before starting the process you should set the environment variable `RESOURCE_GROUP_NAME`, which is used in all scripts.

```bash
export RESOURCE_GROUP_NAME=give_your_name_citus_test_automation_r_g
```

if you want to configure the region, you can also set that:

```bash
export AZURE_REGION=eastus2
```

You should use a single session because the exported variable is only available in the current session and its children sessions. You should start `ssh-agent` and add your key with `ssh-add`.

By default, your public key from `~/.ssh/id_rsa.pub` will be used. This public key will be put to the virtual machines so that you can ssh to them.

To simplify this process, there is a script called `create-cluster.sh`, which:

* creates a resource group from the environment variable `RESOURCE_GROUP_NAME`, and `AZURE_REGION`.
* creates a cluster with the `azuredeploy.json` template in the resource group
* prints the connection string to ssh

then you should run:

```bash
./connect.sh
```

or

```bash
./delete-security-rule.sh
ssh -A pguser@<public ip of coordinator>
```

After you are done with testing, you can delete the resource group with:

```bash
./delete-resource-group.sh
```

Currently the default time for tests 300 seconds, and as we have many tests it might take a while to run all the tests. So when testing a change, it is better to change the test times to something short such as 5 seconds. The time can be changed with the -T parameter:

```bash
pgbench_command: pgbench -c 32 -j 16 -T 300 -P 10 -r

->

pgbench_command: pgbench -c 32 -j 16 -T 5 -P 10 -r

```

If you want to add different vm sizes, you should change the allowed values for `coordinatorVMSize` and `workerVMSize` in `azuredeploy.json`.

We run a custom script to initialize the vms. The script is downloaded to `/var/lib/waagent/custom-script/download/0 `. You can find the script logs
in this file.

</details>

<details>
  <summary>AWS(Deprecated)</summary>

## <a name="aws"></a>AWS

## <a name="getting-started"></a> Getting Started

You can find more information about every step below in other categories. This list of commands show how to get started quickly. Please see other items below to understand details and solve any problems you face.


## <a name="aws-setup-steps"></a> Setup Steps For Each Test

You will need to follow these steps to create a cluster and connect to it, on your local machine:

```bash

# start ssh agent
eval `ssh-agent -s`

# Add your EC2 keypair's private key to your agent
ssh-add path_to_keypair/metin-keypair.pem

# Add your Github ssh key for enterprise (private) repo
ssh-add

# Quickly start a cluster of (1 + 3) c3.4xlarge nodes
cloudformation/create-stack.sh -k metin-keypair -s PgBenchFormation -n 3 -i c3.4xlarge

# When your cluster is ready, it will prompt you with the connection string, connect to master node
ssh -A ec2-user@ec2-35-153-66-69.compute-1.amazonaws.com
```

## <a name="aws-delete-cluster"></a> Steps to delete a cluster

On your local machine:
'
```bash
# Delete the formation
# It's a good practice to check deletion status from the cloud formation console
aws cloudformation delete-stack --stack-name "ScaleFormation"
```

# <a name="detailed-configuration"></a> Detailed Configuration

## <a name="start-a-cluster"></a> Starting a Cluster

You'll need to have installed the [AWS CLI](https://aws.amazon.com/cli/). Once that's
installed you should configure it with `aws configure`. Once it's configured you can run
something like:

`cloudformation/create-stack.sh -k [your keypair name] -s MyStack`

This will take some time (around 7 minutes) and emit some instructions for connecting to
the master node.

The name you pass `-s` must be unique. There are more parameters you can pass such as
`-n`, which changes the number of worker nodes which are launched. If you run
`create-stack` with no parameters it will tell you more.

If you forget the name of your cluster you can get the list of active clusters by running:

`aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE CREATE_IN_PROGRESS CREATE_FAILED --query "StackSummaries[*].{StackName:StackName,StackStatus:StackStatus}"`

This will only list clusters which are in your default region. You can specify a region
with the `--region` flag.

To get the hostname of the master you can run:

`aws cloudformation describe-stacks --stack-name MyStack --query Stacks[0].Outputs[0].OutputValue`

## <a name="connect-to-master"></a> Connecting to the Master

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

</details>

# <a name="running-tests"></a> Running Tests
## <a name="basic-cluster-setup"></a> Basic Cluster Setup

On the coordinator node:

```bash
# Setup your test cluster with PostgreSQL 12.1 and Citus master branch
fab use.postgres:12.1 use.citus:master setup.basic_testing

# Lets change some conf values 
fab pg.set_config:max_wal_size,"'5GB'"
fab pg.set_config:max_connections,1000

# And restart the cluster
fab pg.restart
```


## <a name="pgbench"></a> Running PgBench Tests

On the coordinator node:

```bash
# This will run default pgBench tests with PG=12.1 and Citus Enterprise 9.0 and 8.3 release branches
# and it will log results to pgbench_results_{timemark}.csv file
# Yes, that's all :) You can change settings in fabfile/pgbench_confs/pgbench_default.ini
fab run.pgbench_tests

# It's possible to provide another configuration file for tests
# Such as with this, we run the same set of default pgBench tests without transactions
fab run.pgbench_tests:pgbench_default_without_transaction.ini
```

## <a name="scale"></a> Running Scale Tests

On the coordinator node:

```bash
# This will run scale tests with PG=12.1 and Citus Enterprise 9.0 and 8.3 release branches
# and it will log results to pgbench_results_{timemark}.csv file
# You can change settings in files under the fabfile/pgbench_confs/ directory
fab run.pgbench_tests:scale_test.ini
fab run.pgbench_tests:scale_test_no_index.ini
fab run.pgbench_tests:scale_test_prepared.ini
fab run.pgbench_tests:scale_test_reference.ini
fab run.pgbench_tests:scale_test_foreign.ini
fab run.pgbench_tests:scale_test_100_columns.ini
```

## <a name="pgbench-cloud"></a> Running PgBench Tests Against Hyperscale (Citus)

On the coordinator node:

```bash

# Use pgbench_cloud.ini config file with connection string of your Hyperscale (Citus) cluster
# Don't forget to escape `=` at the end of your connection string
fab run.pgbench_tests:pgbench_cloud.ini,connectionURI='postgres://citus:HJ3iS98CGTOBkwMgXM-RZQ@c.fs4qawhjftbgo7c4f7x3x7ifdpe.db.citusdata.com:5432/citus?sslmode\=require'
```

## <a name="tpch"></a> Running TPC-H Tests

On the coordinator node:

```bash
# This will run TPC-H tests with PG=12.1 and Citus Enterprise 9.0 and 8.3 release branches
# and it will log results to their own files on the home directory. You can use diff to 
# compare results.
# You can change settings in files under the fabfile/tpch_confs/ directory
fab run.tpch_automate

# If you want to run only Q1 with scale factor=1 against community master,
# you can use this config file. Feel free to edit conf file
fab run.tpch_automate:tpch_q1.ini
```

## <a name="tpch-cloud"></a> Running TPC-H Tests Against Hyperscale (Citus)

On the coordinator node:

```bash
# Provide your tpch config file or go with the default file
# Don't forget to escape `=` at the end of your connection string
fab run.tpch_automate:tpch_q1.ini,connectionURI='postgres://citus:dwVg70yBfkZ6hO1WXFyq1Q@c.fhhwxh5watzbizj3folblgbnpbu.db.citusdata.com:5432/citus?sslmode\=require'
```

## <a name="valgrind"></a> Running Valgrind Tests
On the coordinator node:

```bash
# example usage:
# Use PostgreSQL 12.1 and run valgrind test on enterprise/enterprise-master
fab use.valgrind use.postgres:12.1 use.enterprise:enterprise-master run.valgrind
```

## <a name="fab-examples"></a> Example fab Commands

Use `fab --list` to see all the tasks you can run! This is just a few examples.

Once you have a cluster you can use many different variations of the "fab" command to
install Citus:

- `fab --list` will return a list of the tasks you can run.
- `fab setup.basic_testing`, will create a vanilla cluster with postgres and citus. Once this has run you can simply run `psql` to connect to it.
- `fab use.citus:v7.1.1 setup.basic_testing` will do the same, but use the tag `v7.1.1` when installing Citus. You can give it any git ref, it defaults to `master`.
- `fab use.postgres:10.1 setup.basic_testing` lets you choose your postgres version.
- `fab use.enterprise:v7.1.1 setup.enterprise` will install postgres and the `v7.1.1` tag of the enterprise repo.

## <a name="fab-tasks"></a> Tasks, and Ordering of Tasks

When you run a command like `fab use.citus:v7.1.1 setup.basic_testing` you are running two
different tasks: `use.citus` with a `v7.1.1` argument and `setup.basic_testing`. Those
tasks are always executed from left to right, and running them is usually equivalent to
running them as separate commands. For example:

```
# this command:
fab setup.basic_testing add.tpch
# has exactly the same effect as this series of commands:
fab setup.basic_testing
fab add.tpch
```

An exception is the `use` namespace, tasks such as `use.citus` and `use.postgres` only
have an effect on the current command:

```
# this works:
fab use.citus:v7.1.1 setup.basic_testing
# this does not work:
fab use.citus:v7.1.1  # tells fabric to install v7.1.1, but only works during this command
fab setup.basic_testing  # will install the master branch of citus
```

`use` tasks must come before `setup` tasks:

```
# this does not work!
# since the `setup` task is run before the `use` task the `use` task will have no effect
fab setup.basic_testing use.citus:v.7.1.1
```

Finally, there are tasks, such as the ones in the `add` namespace, which asssume a cluster
is already installed and running. They must be run after a `setup` task!


# <a name="task-namespaces"></a> Task Namespaces

## <a name="use"></a> `use` Tasks

These tasks configure the tasks you run after them. When run alone they have no effect.
Some examples:

```
fab use.citus:v7.1.1 setup.basic_testing
fab use.enterprise:v7.1.1 setup.enterprise
fab use.debug_mode use.postgres:10.1 use.citus:v7.1.1 setup.basic_testing
```

`use.debug_mode` passes the following flags to postges' configure: `--enable-debug --enable-cassert CFLAGS="-ggdb -Og -g3 -fno-omit-frame-pointer"`

`use.asserts` passes `--enable-cassert`, it's a subset of `use.debug_mode`.

## <a name="add"></a> `add` Tasks

It is possible to add extra extensions and features to a Citus cluster:

- `fab add.tpch:scale_factor=1,partition_type='hash'` will generate and copy tpch tables.

  The default scale factor is 10. The default partition type is reference for nation, region and supplier and hash for remaining. If you set partition type to 'hash' or 'append', all the tables will be created with that partition type. 
- `fab add.session_analytics` will build and install the session_analytics package (see the instructions above for information on how to checkout this private repo)

For a complete list, run `fab --list`.

As described [above](#fab-tasks), you can run these at the same time as you run `setup` tasks:

- `fab use.citus:v7.1.1 setup.enterprise add.shard_rebalancer` does what you'd expect.

## <a name="pg"></a> `pg` Tasks

These tasks run commands which involve the current postgres instance.

- `fab pg.stop` will stop postgres on all nodes
- `fab pg.restart` will restart postgres on all nodes
- `fab pg.start` guess what this does :)
- `fab pg.read_config:[parameter]` will run `SHOW [parameter]` on all nodes. For example:
- `fab pg.read_config:max_prepared_transactions`

If you want to use a literal comma in a command you must escape it (this applies to all
fab tasks)

- `fab pg.set_config:shared_preload_libraries,'citus\,cstore_fdw'`

Using `pg.set_config` it's possible to get yourself into trouble. `pg.set_config` uses
`ALTER SYSTEM`, so if you've broken your postgres instance so bad it won't boot, you won't
be able to use `pg.set_config` to fix it.

To reset to a clean configuration run this command:

- `fab -- rm pg-latest/data/postgresql.auto.conf`

## <a name="run"></a> `run` Tasks

In order to run pgbench and tpch tests automatically, you can use `run.pgbench_tests` or `run.tpch_automate`. If you want to use default configuration files, running commands without any parameter is enough.

To change configuration file for pgbench tests, you should prepare configuration file similar to fabfile/pgbench_confs/pgbench_config.ini.

To change the configuration file for tpch tests, you should prepare configuration file similar to fabfile/tpch_confs/tpch_default.ini.

# <a name="advanced-fab"></a> Advanced fab Usage

By default your fab commands configure the entire cluster, however you can target roles or
individual machines.

- `fab -R master pg.restart` will restart postgres on the master node.
- `fab -R workers pg.stop` will shutdown pg on all the workers.
- `fab -H 10.0.1.240 pg.start` will start pg on that specific node.

You can also ask to run arbitrary commands by adding them after `--`.

- `fab -H 10.0.1.240 -- cat "max_prepared_transactions=0" >> pg-latest/data/postgresql.conf` will modify the postgresql.conf file on the specified worker.
- `fab -- 'cd citus && git checkout master && make install'` to switch the branch of Citus you're using. (This runs on all nodes)

## <a name="multiple-installs"></a> Using Multiple Citus Installations, `pg-latest`

Some kinds of tests (such as TPC-H) are easier to perform if you create multiple
simultanious installations of Citus and are able to switch between them. The fabric
scripts allow this by maintaining a symlink called `pg-latest`.

Most tasks which interact with a postgres installation (such as `add.cstore` or `pg.stop`)
simply use the installation in `pg-latest`. Tasks such as `setup.basic_testing` which
install postgres will overwrite whatever is currently in `pg-latest`.

You can change where `pg-latest` points by running `fab set_pg_latest:some-absolute-path`. For
example: `fab set_pg_latest:$HOME/enterprise-installation`. Using multiple
installations is a matter of changing your prefix whenever you want to act upon or create
a different installation.

Here's an example:

```bash
fab set_pg_latest:$HOME/pg-960-citus-600
fab use.postgres:9.6.0 use.citus:v6.0.0 setup.basic_testing
fab set_pg_latest:$HOME/pg-961-citus-601
fab use.postgres:9.6.1 use.citus:v6.0.1 setup.basic_testing
# you now have 2 installations of Citus!
fab pg.stop  # stop the existing Citus instance
fab set_pg_latest:$HOME/pg-960-citus-600  # switch to using the new instance
fab pg.start  # start the new instance
# now you've switched back to the first installation

# the above can be abbreviated by writing the following:
fab pg.stop set_pg_latest:$HOME/pg-960-citus-600 pg.start
```
