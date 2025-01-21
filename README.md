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
  * [Running Automated Tests](#running-automated-tests)
  * [Running Automated Hammerdb Benchmark](#running-automated-hammerdb-benchmark)
  * [Running Automated Compatibility Tests](#running-automated-compatibility-tests)
  * [Basic Cluster Setup](#basic-cluster-setup)
  * [Running PgBench Tests](#pgbench)
  * [Running Scale Tests](#scale)
  * [Running Extension Tests](#extension)
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
* [TroubleShooting](#TroubleShooting-test-automation)

## <a name="azure"></a>Azure

## <a name="azure-getting-started"></a> Getting Started

You can find more information about every step below in other categories. This list of commands show how to get started quickly. Please see other items below to understand details and solve any problems you face.

### Prerequisites
1. You should have `az cli` in your local to continue. [Install instructions](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest)
2. Run `az login` to make the CLI log in to your account
3. Make sure that your default subscription is the right one(Azure SQL DB Project Orcas - CitusData):
    ```bash
    # List your subscriptions
    az account list
    # Pick the correct one from the list and run
    az account set --subscription {uuid-of-correct-subscription}
    ```

If your subscriptions list doesn't contain `Azure SQL DB Project Orcas - CitusData`, to add it, contact someone who is authorized.

4. You should use `ssh-agent` to add your ssh keys, which will be used to upload to the release-test-results repository. Note that your keys are kept only in memory, therefore this is a secure step.
    ```bash
    # start ssh agent
    eval `ssh-agent -s`

    # Add your Github ssh key to upload results to release-test-results repo
    ssh-add
    ```

5. You should setup your VPN to be able to connect to Azure VM-s if your tests are not running on GHA. Doing this as of latest consists of:
* Open your VPN.
* Run `routes.ps1` (on Windows only, if you are developing on Mac you should probably ping smn from the team for help). The script requires
`python` to be installed to run.

### General info
In `azuredeploy.parameters.json` file, you will see the parameters that you can change. For example if you want to change the number of workers, you will need to change the parameter `numberOfWorkers`. You can change the type of coordinator and workers separately from the parameters file. Also by default for workers, memory intense vms are used(E type) while for coordinator CPU intense vms are used(D type).

After you run tests, you can see the results in `results` folder. The `results` folder will have the name of the config used for the test.

The data will be stored on the attached disk, size of which can be configured in the parameters.

If you dont specify the region, a random region among `eastus`, `west us 2` and `south central us` will be chosen. This is to use resources uniformly from different regions.

**Port 3456 is used for ssh, you can connect to any node via Port 3456, if you don't use this node, you will hit the security rules.**

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
less azuredeploy.parameters.json

# Quickly start a cluster of with defaults. This will create a resource group and use it for the cluster.
./create-cluster.sh

# connect to the coordinator
./connect.sh
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

We have a special security group which blocks ssh traffic. The rule's priority is 103 and 100, 101, 102 are also taken by this security group.

You can use `connect.sh` which will connect to the coordinator for you on a custom ssh port (at the time of writing 3456).

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

After you are done with testing, you can delete the resource group with:

```bash
./delete-resource-group.sh
```

Currently the default time for tests 300 seconds, and as we have many tests it might take a while to run all the tests. So when testing a change, it is better to change the test times to something short such as 5 seconds. The time can be changed with the -T parameter:

```bash
pgbench_command: pgbench -c 32 -j 16 -T 600 -P 10 -r

->

pgbench_command: pgbench -c 32 -j 16 -T 600 -P 10 -r

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

# Add your Github ssh key for release-test-results repo
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
## <a name="running-automated-tests"></a>Running Automated Tests

**Depending of the tests you trigger here, you can block at most 3 jobs slots in GHA for around 3 hours. Choose wisely the time you want to run the tests to not block development**

If you want, you can run trigger a job which can run pgbench, scale, tpch and extension tests. What the job does is:

* It creates a cluster with the test resource group name
* It connects to the coordinator
* It runs the corresponding test for the job
* It deletes the cluster.

There is a separate job for each test and you can run any combinations of them. To trigger a job, you should create a branch which has specific prefixes.

* If the branch has a prefix `pgbench/`, then pgbench job will be triggered.
* If the branch has a prefix `scale/`, then scale job will be triggered.
* If the branch has a prefix `tpch/`, then tpch job will be triggered.
* If the branch has a prefix `all_performance_test/`, then all jobs will be triggered.
* If the branch has a prefix `extension/`, then extension job will be triggered.

You should push your branch to Github so that the GHA job will be triggerred.

Each job uses a specific resource group name so that there will be at most 3 resource groups for these jobs. If there is already a resource group, then you should make sure that:

* Someone else is currently not running the same test as you

If not, then you can delete the resource group name from portal, you can find it by search the prefix `citusbot`. Under normal circumstances the resource group will already be deleted at the end of the test
even if it fails.

You can find your test results in https://github.com/citusdata/release-test-results under `periodic_job_results` folder. Test results will be pushed to a branch which is in the format ${rg_name}/${month_day_year_uniqueID}.

By default the tests will be run against `release-9.2` and the latest released version. If you want to test on a custom branch you should change the config files of relevant tests with your custom branch name in:

```text
postgres_citus_versions: [('12.1', 'your-custom-branch-name-in-citus'), ('12.1', 'release-9.1')]
```

*Note*: While you can run multiple tests by adding more elements to the array above, the results of the tests after the first might
be inflated due to cache hits (this depends on the tests being run and the type of disks being used by the VM-s). For the fairest
possible comparisons, consider running the tests seperately.

You can change all the settings in these files, the config files for tests are located at:

* pgbench: https://github.com/citusdata/test-automation/tree/master/fabfile/pgbench_confs
* scale: https://github.com/citusdata/test-automation/tree/master/fabfile/pgbench_confs
* tpch: https://github.com/citusdata/test-automation/tree/master/fabfile/tpch_confs
* extension: https://github.com/citusdata/test-automation/tree/master/fabfile/extension_confs

By default, the following tests will be run for each test:

* pgbench: `pgbench_default.ini` and `pgbench_default_without_transaction.ini`
* scale: `scale_test.ini`
* tpch: `tpch_default.ini`
* extension: `extension_default.ini`

If you dont want to use default cluster settings(instance types etc), you can change them in https://github.com/citusdata/test-automation/blob/master/azure/azuredeploy.parameters.json.

If you want to change how long each test will be run, you can change the times with the `-T` parameter. https://github.com/citusdata/test-automation/blob/master/fabfile/pgbench_confs/pgbench_default.ini#L33

```
pgbench_command: pgbench -c 32 -j 16 -T <test time in seconds> -P 10 -r
```

## <a name="running-automated-hammerdb-benchmark"></a>Running Automated Hammerdb Benchmark

**Important:** Push your branch to the github repo even though the HammerDb tests are run from your local.
The initiliazer script used to setup the Azure VM-s will pull your branch from github and not from your local.

Hammerdb tests are run from a driver node. Driver node is in the same virtual network as the cluster.
You can customize the hammerdb cluster in the `hammerdb` folder using `hammerdb/azuredeploy.parameters.json`.
Note that this is the configuration for the cluster, which is separate than benchmark configurations(`fabfile/hammerdb_confs/`)

In `fabfile/hammerdb_confs` you can add more configs to this folder:

* change postgres version
* use a custom branch (You can also use git refs instead of branch names)
* change/add postgres/citus settings

You can add as many configs as you want to `fabfile/hammerdb_confs` folder and the automation tool will
run the benchmark for each config. So if you want to compare two branches, you can create two identical config files with two different branches. (Note that you can also use git refs instead of branch names)
Even though the script will vacuum the tables in each iteration to get more accurate results, the disk
cache is likely to inflate the results of the tests running after the first file so for the most unbiased results
test the setups seperately (repeat this produre twice).
The result logs will contain the config file so that it is easy to know which config was used for a run.

After adding the configs `fabfile/hammerdb_confs` could look like:

* ./master.ini
* ./some_branch.ini
* ./some_other_branch.ini

In order to run hammerdb benchmark:

```bash
eval `ssh-agent -s`
ssh-add
export RESOURCE_GROUP_NAME=<your resource group name>
export GIT_USERNAME=<Your github username>
export GIT_TOKEN=<Your github token with repo, write:packages and read:packages permissions> # You can create a github token from https://github.com/settings/tokens
cd hammerdb
# YOU SHOULD CREATE A NEW BRANCH AND CHANGE THE SETTINGS/CONFIGURATIONS IN THE NEW BRANCH
# AND PUSH THE BRANCH SO THAT WHEN THE TOOL CLONES THE REPOSITORY
# IT CAN DOWNLOAD YOUR BRANCH.
vim fabfile/hammerdb_confs/<branch_name>.ini # verify that your custom config file is correct
./create-run.sh
# you will be given a command to connect to the driver node and what
# to run afterwards.
```

**After running ./create-run.sh you do not have to be connected to the driver node at all, it will take care of the rest for you.**

The cluster deployment is flaky and sometimes it will fail. This behaviour is somewhat rare so it is not a
big problem. In that case, simply delete the previous resource group, and try again.
You can do that with:
```bash
# running from the same shell where you called create-run.sh to start the test
../azure/delete-resource-group.sh
./create-run.sh
```

If it is persistent, some policy might have been changed on Azure so either consider debugging the issue,
or opening an issue in test-automation.

**The cluster will be deleted if everything goes okay, but you should check if it is deleted to be on the safe side.(If it is not, you can delete that with azure/delete-resource-group.sh or from the portal).**

In order to see the process of the tests, from the driver node:

```bash
./connect-driver.sh
screen -r
```

You can see the screen logs in `~/screenlog.0`.

You will see the results in a branch `hammerdb_date_id` in https://github.com/citusdata/release-test-results.
You won't get any notifications for the results, so you will need to manually check it.
What files are pushed to github:

* build.tcl (This is the configuration file used for building hammerdb tables)
* run.tcl (This is the configuration file used for running hammerdb tpcc benchmark)
* build_<config_file_name>.log (These are the outputs of building the hammerdb tables for the 'config_file_name')
* run_<config_file_name>.log (These are the outputs of running hammerdb tpcc benchmark for the 'config_file_name')
* ch_benchmarks.log (This is the log file that is generated from ch-benCHmark script)
* ch_results.txt (This is the file that contains the results of ch benchmark, each config file's result is saved in a new line)
* <config_file_name>.NOPM.log (These are the files that contains the NOPM for the given config file name.)

`hammerdb/build.tcl` creates and fills hammerdb tpcc tables. You should have at least 1:5 ratio for vuuser:warehouse_count otherwise the build.tcl might get stuck.

`hammerdb/run.tcl` runs tpcc benchmark. You can configure things such as test duration here.

Note that running a benchmark with a single config file with a vuuser of 250 and 1000 warehouses could
take around 2-3 hours. (the whole process)

If you want to run only the tpcc benchmark or the analytical queries, you should change the `is_tpcc` and `is_ch` variables in `create-run.sh`. For example if you want to run only tpcc benchmarks, you should set `is_tpcc` to `true` and `is_ch` to `false` (Alternatively you can see `IS_CH` and `IS_TPCC` environment variables). When you are only running the analytical queries, you can also specify how long you want them to be run by changing the `DEFAULT_CH_RUNTIME_IN_SECS` variable in `build-and-run.sh`. By default it will be run 3600 seconds.

You can change the thread count and initial sleep time for analytical queries from `build-and-run.sh` with `CH_THREAD_COUNT` and `RAMPUP_TIME` variables respectively.

If you want to run hammerdb4.0 change `hammerdb_version` to `4.0` in `create-run.sh`.

By default a random region will be used, if you want you can specify the region with `AZURE_REGION` environment variable prior to running `create-run.sh` such as `export AZURE_REGION=westus2`.

## <a name="running-automated-compatibility-tests"></a>Running Automated Copatibility Tests
Currently, only testing compatibility with jdbc is automated.
To run, create a branch called `jdbc/{whatever-you-want}` and push to origin.
The citus branch and jdbc version can be configured from [JDBC Config](jdbc/jdbc_config.json)

For more details read: [JDBC README](jdbc/README.md)

## <a name="basic-cluster-setup"></a> Basic Cluster Setup

On the coordinator node:

```bash
# Setup your test cluster with PostgreSQL 12.1 and Citus master branch
fab use.postgres 12.1 use.citus master setup.basic-testing

# Lets change some conf values
fab pg.set-config max_wal_size "'5GB'"
fab pg.set-config max_connections 1000

# And restart the cluster
fab pg.restart
```

If you want to add the coordinator to the cluster, you can run:

```bash
fab add.coordinator-to-metadata
```

If you want the coordinator to have shards, you can run:

```bash
fab add.shards-on-coordinator
```

## <a name="pgbench"></a> Running PgBench Tests

On the coordinator node:

```bash
# This will run default pgBench tests with PG=12.1 and Citus 9.2 and 8.3 release branches
# and it will log results to pgbench_results_{timemark}.csv file
# Yes, that's all :) You can change settings in fabfile/pgbench_confs/pgbench_default.ini
fab run.pgbench-tests

# It's possible to provide another configuration file for tests
# Such as with this, we run the same set of default pgBench tests without transactions
fab run.pgbench-tests --config-file=pgbench_default_without_transaction.ini
```

## <a name="scale"></a> Running Scale Tests

On the coordinator node:

```bash
# This will run scale tests with PG=12.1 and Citus 9.2 and 8.3 release branches
# and it will log results to pgbench_results_{timemark}.csv file
# You can change settings in files under the fabfile/pgbench_confs/ directory
fab run.pgbench-tests --config-file=scale_test.ini
fab run.pgbench-tests --config-file=scale_test_no_index.ini
fab run.pgbench-tests --config-file=scale_test_prepared.ini
fab run.pgbench-tests --config-file=scale_test_reference.ini
fab run.pgbench-tests --config-file=scale_test_foreign.ini
fab run.pgbench-tests --config-file=scale_test_100_columns.ini
```

## <a name="extension"></a> Running Extension Tests

You can execute a PG extension's regression tests with any combination of other extensions created in the database. The purpose of those tests is to figure out if any test fails due to having those extensions together. Currently we only support extensions whose tests can be run by pg_regress. We do not support any other extensions whose tests are run by some other tools. e.g. tap tests

Here is the schema for main section:

```
[main]
postgres_versions: [<string>]   specifies Postgres versions for which the test should be repeated
extensions: [<string>]          specifies the extensions for which we give information
test_count: <integer>           specifies total test scenarios which uses any extensions amongst the extension definitions


[main]
postgres_versions: ['14.5']
extensions: ['citus', 'hll', 'topn', 'tdigest', 'auto_explain']
test_count: 4
```

Here is the schema for an extension definition:

```
[<string>]                    specifies the extension name (that should be the same name with the extension name used in 'create extension <extension_name>;')
contrib: <bool>               specifies if the extension exists in contrib folder under Postgres (we do not install if it is a contrib extension because it is bundled with Postgres)
preload: <bool>               specifies if we should add the extension into shared_preload_libraries
create: <bool>                specifies if we should create extension in database (for example: 'create extension auto_explain;' causes error because it does not add any object)
configure: <bool>             specifies if the installation step has a configure step (i.e. ./configure)
repo_url: <string>            specifies repo url for non-contrib extension
git_ref: <string>             specifies repo branch name for non-contrib extension
relative_test_path: <string>  specifies relative directory in which pg_regress will run the tests
conf_string: <string>         specifies optional postgres.conf options
post_create_hook: <string>    specifies optional method name to be called after the extension is created. You should implement the hook in fabfile/extension_hooks.py.


[tdigest]
contrib: False
preload: False
create: True
configure: False
repo_url: https://github.com/tvondra/tdigest.git
git_ref: v1.4.0
relative_test_path: .
```

Here is the schema for a test case:

```
[test-<integer>]                  specifies the test name
ext_to_test: <string>             specifies the extension to be tested
dep_order: <string>               specifies the shared_preload_libraries string order
test_command: <string>            specifies the test command
conf_string: <string>             specifies the postgres configurations to be used in the test


[test-4]
ext_to_test: citus
dep_order: citus,auto_explain
test_command: make check-vanilla
conf_string: '''
    auto_explain.log_min_duration=0
    auto_explain.log_analyze=1
    auto_explain.log_buffers=1
    auto_explain.log_nested_statements=1
    '''
```

On the coordinator node:

```bash
# This will run default extension tests with PG=14.5
# Yes, that's all :) You can change settings in fabfile/extension_confs/extension_default.ini
fab run.extension-tests

# It's possible to provide another configuration file for tests
fab run.extension-tests --config-file=[other_config.ini]
```

## <a name="extension"></a> Running Extension Tests

You can execute a PG extension's regression tests with any combination of other extensions created in the database. The purpose of those tests is to figure out if any test fails due to having those extensions together. Currently we only support extensions whose tests can be run by pg_regress. We do not support any other extensions whose tests are run by some other tools. e.g. tap tests

Here is the schema for main section:

```
[main]
postgres_versions: [<string>]   specifies Postgres versions for which the test should be repeated
extensions: [<string>]          specifies the extensions for which we give information
test_count: <integer>           specifies total test scenarios which uses any extensions amongst the extension definitions


[main]
postgres_versions: ['14.5']
extensions: ['citus', 'hll', 'topn', 'tdigest', 'auto_explain']
test_count: 4
```

Here is the schema for an extension definition:

```
[<string>]                    specifies the extension name (that should be the same name with the extension name used in 'create extension <extension_name>;')
contrib: <bool>               specifies if the extension exists in contrib folder under Postgres (we do not install if it is a contrib extension because it is bundled with Postgres)
preload: <bool>               specifies if we should add the extension into shared_preload_libraries
create: <bool>                specifies if we should create extension in database (for example: 'create extension auto_explain;' causes error because it does not add any object)
configure: <bool>             specifies if the installation step has a configure step (i.e. ./configure)
repo_url: <string>            specifies repo url for non-contrib extension
git_ref: <string>             specifies repo branch name for non-contrib extension
relative_test_path: <string>  specifies relative directory in which pg_regress will run the tests
conf_string: <string>         specifies optional postgres.conf options
post_create_hook: <string>    specifies optional method name to be called after the extension is created. You should implement the hook in fabfile/extension_hooks.py.


[tdigest]
contrib: False
preload: False
create: True
configure: False
repo_url: https://github.com/tvondra/tdigest.git
git_ref: v1.4.0
relative_test_path: .
```

Here is the schema for a test case:

```
[test-<integer>]                  specifies the test name
ext_to_test: <string>             specifies the extension to be tested
dep_order: <string>               specifies the shared_preload_libraries string order
test_command: <string>            specifies the test command
conf_string: <string>             specifies the postgres configurations to be used in the test


[test-4]
ext_to_test: citus
dep_order: citus,auto_explain
test_command: make check-vanilla
conf_string: '''
    auto_explain.log_min_duration=0
    auto_explain.log_analyze=1
    auto_explain.log_buffers=1
    auto_explain.log_nested_statements=1
    '''
```

On the coordinator node:

```bash
# This will run default extension tests with PG=14.5
# Yes, that's all :) You can change settings in fabfile/extension_confs/extension_default.ini
fab run.extension-tests

# It's possible to provide another configuration file for tests
fab run.extension-tests:[other_config.ini]
```

**Note**: You should `export EXTENSION_TEST=1` before running `create-cluster.sh` if you plan to run extension tests.

## <a name="pgbench-cloud"></a> Running PgBench Tests Against Hyperscale (Citus)

On the coordinator node:

```bash

# Use pgbench_cloud.ini config file with connection string of your Hyperscale (Citus) cluster
# Don't forget to escape `=` at the end of your connection string
fab run.pgbench-tests --config-file=pgbench_cloud.ini --connectionURI='postgres://citus:HJ3iS98CGTOBkwMgXM-RZQ@c.fs4qawhjftbgo7c4f7x3x7ifdpe.db.citusdata.com:5432/citus?sslmode\=require'
```

**Important Note**
- If an extension is a contrib module, then any url and branch will be discarded. If it is not a contrib module, url and branch is required.
- `conf_string` is optional both for extension and test case definitions.

## <a name="tpch"></a> Running TPC-H Tests

On the coordinator node:

```bash
# This will run TPC-H tests with PG=12.1 and Citus 9.2 and 8.3 release branches
# and it will log results to their own files on the home directory. You can use diff to
# compare results.
# You can change settings in files under the fabfile/tpch_confs/ directory
fab run.tpch-automate

# If you want to run only Q1 with scale factor=1 against community master,
# you can use this config file. Feel free to edit conf file
fab run.tpch-automate --config-file=tpch_q1.ini
```

## <a name="tpch-cloud"></a> Running TPC-H Tests Against Hyperscale (Citus)

On the coordinator node:

```bash
# Provide your tpch config file or go with the default file
# Don't forget to escape `=` at the end of your connection string
fab run.tpch-automate --config-file=tpch_q1.ini --connectionURI='postgres://citus:dwVg70yBfkZ6hO1WXFyq1Q@c.fhhwxh5watzbizj3folblgbnpbu.db.citusdata.com:5432/citus?sslmode\=require'
```

## <a name="valgrind"></a> Running Valgrind Tests

0. We have a simple Dockerfile that provides a valgrind environment for Citus and a simple bash script that can
   be used to run a valgrind test target on a container created from that Dockerfile. Both of them are
   located in the `valgrind` directory.

   The only reason that we use a Docker container for valgrind tests is to be able to use the vm for multiple
   valgrind test targets in parallel at the same time. Otherwise, since Citus test suite makes certain
   assumptions about the environment, like the port number used for coordinator and worker nodes, we cannot
   run multiple valgrind test targets in parallel on the same vm.

1. You can either choose to run the valgrind tests on your local machine or on a remote machine; and you can
   choose to create the remote machine by yourself or use our usual `create-cluster.sh` script.

   If you already have remote machine, you can simply clone this repository there and skip this step.

   Otherwise, here are the steps to create a remote machine via `create-cluster.sh` script.

   You need to do the following before following the steps in [Setup Steps For Each Test](#azure-setup-steps)
   to execute `create-cluster.sh`:

   ```bash
   eval `ssh-agent -s`
   ssh-add

   export VALGRIND_TEST=1
   ```

   Setting `VALGRIND_TEST` environment variable to `1` makes `numberOfWorkers` setting useless.
   This is because we will already use our regression test structure and it creates a local cluster
   itself.

   Now you can connect to your remote machine by using `./connect.sh` script.

2. Create a directory that will be used to store the results of the valgrind tests, as in the example below:

   ```bash
   mkdir -p ~/vglogs/
   ```

3. Now, for each valgrind test target that you want to run, you need to run the following command,
   **preferably in a screen / tmux session** because valgrind tests can take a very long time:

   ```bash
   ./run.sh 17.2 release-13.0 multi_1_schedule ~/vglogs/
   ```

   This command will run the `multi_1_schedule` test target on the `release-13.0` branch of Citus under valgrind,
   using the  `17.2` version of PostgreSQL, and store the results in a new subdirectory of `~/vglogs/`. Also,
   rather than providing the Citus branch name, it's doable and more preferable to provide a commit hash to ensure
   that the tests are run on the exact commit that you want to test.

   Note that you can use any valid schedule name for regression, isolation or failure tests here. `run.sh` script
   will automatically determine the custom valgrind check targets for the given schedule name by searching
   certain keywords in the schedule name, like "isolation" and "failure".

4. Finally, investigate the logs, especially `citus_valgrind_test_log.txt` for any memory errors that seem to be
   caused by Citus.

   `run.sh` will also try to copy `regression.diffs` and `regression.out` files from the container to the host
   but it's quite normal if you see such error messages while it's trying to do that:
   ```bash
   Error response from daemon: Could not find the file /citus/src/test/regress/regression.diffs in container citus-vg-...
   Error response from daemon: Could not find the file /citus/src/test/regress/regression.out in container citus-vg-...
   ```

   This happens when the regression test run was successful and so Postgres test suite removed these files. Note
   that the tests being successful doesn't indicate that there are no memory errors, so you still need to check
   the `citus_valgrind_test_log.txt` file. And similarly, some of the regression tests that normally don't fail
   in Citus CI can fail under valgrind and this is also normal -unless no processes exit with status code `2`,
   which indicates a crash- because valgrind heavily slows down the tests and this usually results in test failures
   due to timeouts.

5. Delete the resource group if you created a new one for the valgrind tests.

## <a name="fab-examples"></a> Example fab Commands

Use `fab --list` to see all the tasks you can run! This is just a few examples.

Once you have a cluster you can use many different variations of the "fab" command to
install Citus:

- `fab --list` will return a list of the tasks you can run.
- `fab setup.basic-testing`, will create a vanilla cluster with postgres and citus. Once this has run you can simply run `psql` to connect to it.
- `fab use.citus v7.1.1 setup.basic-testing` will do the same, but use the tag `v7.1.1` when installing Citus. You can give it any git ref, it defaults to `master`.
- `fab use.postgres 10.1 setup.basic-testing` lets you choose your postgres version.
- `fab use.citus release-9.2 setup.citus` will install postgres and the `release-9.2` branch of the citus repo.

## <a name="fab-tasks"></a> Tasks, and Ordering of Tasks

When you run a command like `fab use.citus v7.1.1 setup.basic-testing` you are running two
different tasks: `use.citus` with a `v7.1.1` argument and `setup.basic-testing`. Those
tasks are always executed from left to right, and running them is usually equivalent to
running them as separate commands. For example:

```
# this command:
fab setup.basic-testing add.tpch
# has exactly the same effect as this series of commands:
fab setup.basic-testing
fab add.tpch
```

An exception is the `use` namespace, tasks such as `use.citus` and `use.postgres` only
have an effect on the current command:

```
# this works:
fab use.citus v7.1.1 setup.basic-testing
# this does not work:
fab use.citus v7.1.1  # tells fabric to install v7.1.1, but only works during this command
fab setup.basic-testing  # will install the master branch of citus
```

`use` tasks must come before `setup` tasks:

```
# this does not work!
# since the `setup` task is run before the `use` task the `use` task will have no effect
fab setup.basic-testing use.citus v.7.1.1
```

Finally, there are tasks, such as the ones in the `add` namespace, which asssume a cluster
is already installed and running. They must be run after a `setup` task!


# <a name="task-namespaces"></a> Task Namespaces

## <a name="use"></a> `use` Tasks

These tasks configure the tasks you run after them. When run alone they have no effect.
Some examples:

```
fab use.citus v7.1.1 setup.basic-testing
fab use.citus release-9.2 setup.citus
fab use.debug-mode use.postgres 10.1 use.citus v7.1.1 setup.basic-testing
```

`use.debug-mode` passes the following flags to postges' configure: `--enable-debug --enable-cassert CFLAGS="-ggdb -Og -g3 -fno-omit-frame-pointer"`

`use.asserts` passes `--enable-cassert`, it's a subset of `use.debug-mode`.

## <a name="add"></a> `add` Tasks

It is possible to add extra extensions and features to a Citus cluster:

- `fab add.tpch --scale-factor=1 --partition-type=hash` will generate and copy tpch tables.

  The default scale factor is 10. The default partition type is reference for nation, region and supplier and hash for remaining. If you set partition type to 'hash' or 'append', all the tables will be created with that partition type.
- `fab add.session_analytics` will build and install the session_analytics package (see the instructions above for information on how to checkout this private repo)

For a complete list, run `fab --list`.

As described [above](#fab-tasks), you can run these at the same time as you run `setup` tasks:

- `fab use.citus v7.1.1 setup.citus add.shard_rebalancer` does what you'd expect.

## <a name="pg"></a> `pg` Tasks

These tasks run commands which involve the current postgres instance.

- `fab pg.stop` will stop postgres on all nodes
- `fab pg.restart` will restart postgres on all nodes
- `fab pg.start` guess what this does :)
- `fab pg.read-config [parameter]` will run `SHOW [parameter]` on all nodes. For example:
- `fab pg.read-config max_prepared_transactions`

If you want to use a literal comma in a command you must escape it (this applies to all
fab tasks)

- `fab pg.set-config shared_preload_libraries 'citus\,cstore_fdw'`

Using `pg.set-config` it's possible to get yourself into trouble. `pg.set-config` uses
`ALTER SYSTEM`, so if you've broken your postgres instance so bad it won't boot, you won't
be able to use `pg.set-config` to fix it.

To reset to a clean configuration run this command:

- `fab -- rm pg-latest/data/postgresql.auto.conf`

## <a name="run"></a> `run` Tasks

In order to run pgbench and tpch tests automatically, you can use `run.pgbench_tests` or `run.tpch_automate`. If you want to use default configuration files, running commands without any parameter is enough.

To change configuration file for pgbench tests, you should prepare configuration file similar to fabfile/pgbench_confs/pgbench_config.ini.

To change the configuration file for tpch tests, you should prepare configuration file similar to fabfile/tpch_confs/tpch_default.ini.

# <a name="advanced-fab"></a> Advanced fab Usage

By default your fab commands configure the entire cluster, however you can target individual machines.

- `fab -H 10.0.1.240 pg.start` will start pg on that specific node.

You can also ask to run arbitrary commands by adding them after `--`.

- `fab -H 10.0.1.240 -- cat "max_prepared_transactions=0" >> pg-latest/data/postgresql.conf` will modify the postgresql.conf file on the specified worker.
- `fab -- 'cd citus && git checkout master && make install'` to switch the branch of Citus you're using. (This runs on all nodes)

## <a name="multiple-installs"></a> Using Multiple Citus Installations, `pg-latest`

Some kinds of tests (such as TPC-H) are easier to perform if you create multiple
simultanious installations of Citus and are able to switch between them. The fabric
scripts allow this by maintaining a symlink called `pg-latest`.

Most tasks which interact with a postgres installation (such as `add.cstore` or `pg.stop`)
simply use the installation in `pg-latest`. Tasks such as `setup.basic-testing` which
install postgres will overwrite whatever is currently in `pg-latest`.

You can change where `pg-latest` points by running `fab set-pg-latest some-absolute-path`. For
example: `fab set-pg-latest $HOME/postgres-installation`. Using multiple
installations is a matter of changing your prefix whenever you want to act upon or create
a different installation.

Here's an example:

```bash
fab set-pg-latest $HOME/pg-960-citus-600
fab use.postgres 9.6.0 use.citus v6.0.0 setup.basic-testing
fab set-pg-latest $HOME/pg-961-citus-601
fab use.postgres 9.6.1 use.citus v6.0.1 setup.basic-testing
# you now have 2 installations of Citus!
fab pg.stop  # stop the existing Citus instance
fab set-pg-latest $HOME/pg-960-citus-600  # switch to using the new instance
fab pg.start  # start the new instance
# now you've switched back to the first installation

# the above can be abbreviated by writing the following:
fab pg.stop set-pg-latest $HOME/pg-960-citus-600 pg.start
```

## <a name="TroubleShooting-test-automation"></a> TroubleShooting

Currently test automation has a lot of dependencies such as fabfile, azure and more. In general failures are temporary, which may be as long as a few days(If the problem is on azure service). In that case there is nothing we can do, but sometimes there are other problems that we can fix, and it is useful to try some of the following steps in that case:

- Even if a creation of a cluster fails, you can still see the logs and what caused the problem:

  * Find the public ip address of any instance (connect scripts might not be available if the cluster is in an incorrect state)
  * Connect to the machine `ssh pguser@<public_ip>`
  * switch to the root user(since `pguser` doesn't have the access to the logs) `sudo su root`
  * cd into the log directory `/var/lib/waagent/custom-script/download/0`
  * Now you can look at the `stderr` or `stdout` to see what went unexpected.

- Updating `az cli` is also mostly a good option, follow the installation instructions in https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-linux to update your local `az cli` installation.

- If you suspect if a particular `az foo bar` command doesn't work as expected, you could also insert `--debug` to have a closer look.

-  If you're consistently having connection timeout errors (255) when trying to connect to a VM, then consider setting `AZURE_REGION` environment variable to `eastus`. This error will likely occur due to connection policy issues. As of latest, setting up your VPN properly should fix this issue.

- While running on Azure VM-s there might be deployment errors (go to your resource group overview in the portal). This might be caused due to changing
network security policies in Azure. The error message of the deployment failure should show the conflicting policies. You can then go to the `azuredeploy.json` file for your test and try to change the priority of the custom policies (search priority in the file) until there are no conflicts.
