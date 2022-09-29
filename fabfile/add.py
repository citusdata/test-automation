import os.path
from os import listdir
import re

from invoke import task
from invoke.exceptions import Exit

import utils
import config
import prefix
import pg

__all__ = [
    'tpch', 'jdbc', 'coordinator_to_metadata', 'shards_on_coordinator'
]

def repo_path_for_url(c, repo_url):
    repo_name = c.run('basename {}'.format(repo_url))
    repo_name = repo_name.split('.')[0] # chop off the '.git' at the end
    return os.path.join(config.CODE_DIRECTORY, repo_name)

class InstallExtensionTask:
    '''
    A class which has all the boilerplate for building and installing extensions.
    Instantiate it to make it show up in the list of tasks.

    Tasks created with this class accept a single parameter, the git revision to check out
    and build. e.x. `fab add.shard_rebalancer:master`. Will default to using 'master'
    unless you specify otherwise by passing 'default_git_ref'.
    '''

    def __init__(self, task_name, doc, repo_url, **kwargs):
        self.name = task_name  # the name of the task (fab [xxx])
        self.__doc__ = doc  # the description which fab --list will list
        self.repo_url = repo_url
        self.default_git_ref = kwargs.get('default_git_ref', 'master')
        self.before_run_hook = kwargs.get('before_run_hook', None)
        self.post_install_hook = kwargs.get('post_install_hook', None)

        super(InstallExtensionTask, self).__init__()

    def run(self, c, *args):
        if self.before_run_hook:
            self.before_run_hook(c)

        self.repo_path = repo_path_for_url(self.repo_url)

        prefix.check_for_pg_latest(c)  # make sure we're pointed at a real instance
        utils.add_github_to_known_hosts(c) # make sure ssh doesn't prompt

        if len(args) == 0:
            git_ref = self.default_git_ref
        else:
            git_ref = args[0]

        utils.rmdir(c, self.repo_path, force=True) # force because git write-protects files
        c.run('git clone -q {} {}'.format(self.repo_url, self.repo_path))

        with c.cd(self.repo_path), path('{}/bin'.format(config.PG_LATEST)):
            c.run('git checkout {}'.format(git_ref))
            c.run('make install')

        if self.post_install_hook:
            self.post_install_hook(c)


class RegressExtensionTask():
    '''
    A class which has all the boilerplate for run regression tests for an already installed extension.
    '''

    def __init__(self, task_name, doc, repo_url, **kwargs):
        self.name = task_name  # the name of the task (fab [xxx])
        self.__doc__ = doc  # the description which fab --list will list
        self.repo_url = repo_url
        self.default_git_ref = kwargs.get('default_git_ref', 'master')

        super(RegressExtensionTask, self).__init__()

    def run(self, c, *args):
        self.repo_path = repo_path_for_url(c, self.repo_url)

        # force drop contrib_regression_db if exists, some backend still use db, so drop db not works
        utils.psql(c, "DROP DATABASE IF EXISTS contrib_regression WITH (FORCE);")

        # create result folder if not exists
        utils.mkdir_if_not_exists(config.RESULTS_DIRECTORY)

        # add --load-extension=citus to REGRESS_OPTS
        with c.cd(self.repo_path):
            c.run("echo 'REGRESS_OPTS := $(REGRESS_OPTS) --load-extension=citus' >> Makefile")

        # run tests with warn option to not exit in case of a test failure in the extension,
        # because we want to run regression tests for other extensions too.
        with c.cd(self.repo_path):
            c.run("make installcheck", warn=True)

        # rename regression.diffs, if exists, so that extension's diff file does not conflict with others'        
        self.rename_regression_diff(c)

    def rename_regression_diff(self, c):
        regression_diffs_path = os.path.join(self.repo_path, config.REGRESSION_DIFFS_FILE)
        if os.path.isfile(regression_diffs_path):
            extension_regression_diff = config.REGRESSION_DIFFS_FILE + '_ext_' + self.name
            with c.cd(config.RESULTS_DIRECTORY):
                c.run('mv {} {}'.format(regression_diffs_path, extension_regression_diff))

@task
def tpch(c, **kwargs):
    'Generates and loads tpc-h data into the instance at pg-latest'
    prefix.check_for_pg_latest(c)

    psql = '{}/bin/psql'.format(config.PG_LATEST)

    connectionURI = kwargs.get('connectionURI', kwargs.get('connectionURI', ''))
    scale = kwargs.get('scale-factor', kwargs.get('scale_factor', 10))
    partition_type = kwargs.get('partition-type', kwargs.get('partition_type', 'default'))

    # generate tpc-h data
    tpch_path = '{}/tpch_2_13_0'.format(config.TESTS_REPO)
    with c.cd(tpch_path):
        c.run('make')
        c.run('SCALE_FACTOR={} CHUNKS="o 24 c 4 P 1 S 4 s 1" sh generate2.sh'.format(scale))

        # clear old tables
        c.run('{} {} -f drop_tables.sql'.format(psql, connectionURI))

        # create the tpc-h tables
        if partition_type == 'default':
            c.run('{} {} -f tpch_create_tables.ddl'.format(psql, connectionURI))
        elif partition_type == 'hash':
            c.run('{} {} -f tpch_create_hash_partitioned_tables.ddl'.format(psql, connectionURI))
        elif partition_type == 'append':
            c.run('{} {} -f tpch_create_append_partitioned_tables.ddl'.format(psql, connectionURI))

        # stage tpc-h data
        for segment in c.run('find {} -name \'*.tbl*\''.format(tpch_path)).splitlines():
            table_name = os.path.basename(segment).split('.')[0]
            c.run('''{} {} -c "\COPY {} FROM '{}' WITH DELIMITER '|'"'''.format(psql, connectionURI, table_name, segment))

        c.run('{} {} -f warm_up_cache.sql'.format(psql, connectionURI))

@task
def jdbc(c):
    'Adds everything required to test out the jdbc connecter'
    c.sudo('yum install -q -y java-1.6.0-openjdk-devel') # we only need java on the master

@task
def coordinator_to_metadata(c):
    local_ip = utils.get_local_ip()
    utils.psql(c, "SELECT master_add_node('{}', {}, groupid => 0);".format(local_ip, config.PORT))

@task
def shards_on_coordinator(c):
    local_ip = utils.get_local_ip()
    utils.psql(c, "SELECT 1 FROM master_set_node_property('{}', {}, 'shouldhaveshards', true);"
        .format(local_ip, config.PORT))    