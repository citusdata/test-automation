import os.path
from os import listdir
import glob
import re

from fabric.api import task, cd, path, run, roles, sudo, abort, execute
from fabric.tasks import Task
from fabric.context_managers import settings

import utils
import config
import prefix
import pg

__all__ = [
    'session_analytics', 'cstore', 'tpch', 'jdbc', 'shard_rebalancer', 
    'coordinator_to_metadata', 'shards_on_coordinator'
]

class InstallExtensionTask(Task):
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
        self.schedule_name = 'ext_schedule'
        self.repo_url = repo_url

        self.default_git_ref = kwargs.get('default_git_ref', 'master')
        self.before_run_hook = kwargs.get('before_run_hook', None)
        self.post_install_hook = kwargs.get('post_install_hook', None)
        self.before_regression_hook = kwargs.get('before_regression_hook', None)

        super(InstallExtensionTask, self).__init__()

    @staticmethod
    def repo_path_for_url(repo_url):
        repo_name = run('basename {}'.format(repo_url))
        repo_name = repo_name.split('.')[0] # chop off the '.git' at the end
        return os.path.join(config.CODE_DIRECTORY, repo_name)

    def run(self, *args):
        if self.before_run_hook:
            self.before_run_hook()

        prefix.check_for_pg_latest()  # make sure we're pointed at a real instance
        utils.add_github_to_known_hosts() # make sure ssh doesn't prompt

        if len(args) == 0:
            git_ref = self.default_git_ref
        else:
            git_ref = args[0]

        repo = self.repo_path_for_url(self.repo_url)

        utils.rmdir(repo, force=True) # force because git write-protects files
        run('git clone -q {} {}'.format(self.repo_url, repo))

        with cd(repo), path('{}/bin'.format(config.PG_LATEST)):
            run('git checkout {}'.format(git_ref))
            run('make install')

        if self.post_install_hook:
            self.post_install_hook()

    def create_extension(self):
        utils.psql('CREATE EXTENSION {} CASCADE;'.format(self.name))

    def setup_schedule_tests(self, schedule_tests):
        # set schedule tests
        with cd(self.test_input_dir):
            run('touch {}'.format(self.schedule_name))
            for schedule_test in schedule_tests:
                run('echo test: {} >> {}'.format(schedule_test, self.schedule_name))

    def rename_regression_diff(self):
        with cd(config.RESULTS_DIRECTORY):
            regression_diffs_path = os.path.join(config.RESULTS_DIRECTORY, config.REGRESSION_DIFFS_FILE)
            if os.path.isfile(regression_diffs_path):
                extension_regression_diff = config.REGRESSION_DIFFS_FILE + '_ext_' + self.name
                run('mv {} {}'.format(config.REGRESSION_DIFFS_FILE, extension_regression_diff))

    def before_regression_common(self):
        repo_path = self.repo_path_for_url(self.repo_url)
        self.test_input_dir = repo_path

        self.db = run('whoami')
        self.user = run('whoami')

        # alter default db's lc_monetary to C
        utils.psql('ALTER DATABASE {} SET lc_monetary TO \'C\';'.format(self.db))

        # create result folder if not exists
        utils.mkdir_if_not_exists(config.RESULTS_DIRECTORY) 

    def regression(self):
        self.before_regression_common()
        if self.before_regression_hook:
            self.before_regression_hook(self)        
        
        # run pg_regress with warn_only option to not exit in case of a test failure in the extension,
        # because we want to run regression tests for other extensions too.
        pgxsdir = run('dirname $({}/bin/pg_config --pgxs)'.format(config.PG_LATEST))
        pg_regress = "{}/../test/regress/pg_regress".format(pgxsdir)

        with settings(warn_only=True):
            run("{} --inputdir {} --outputdir {} --schedule {}/{} --use-existing --user {} --dbname {}".format(
                pg_regress, self.test_input_dir, config.RESULTS_DIRECTORY, self.test_input_dir, self.schedule_name, self.user, self.db
            ))

        # rename regression.diffs, if exists, so that extension's diff file does not conflict with others'        
        self.rename_regression_diff()

session_analytics = InstallExtensionTask(
    task_name='session_analytics',
    doc='Adds the session analytics extension to the instance in pg-latest',
    repo_url='git@github.com:citusdata/session_analytics.git',
)

def before_regression_hll(hll_task):    
    repo_path = InstallExtensionTask.repo_path_for_url(hll_task.repo_url)

    # set schedule tests
    schedule_tests = """setup add_agg agg_oob auto_sparse card_op cast_shape copy_binary cumulative_add_cardinality_correction cumulative_add_comprehensive_promotion
                        cumulative_add_sparse_edge cumulative_add_sparse_random cumulative_add_sparse_step cumulative_union_comprehensive cumulative_union_explicit_explicit
                        cumulative_union_explicit_promotion cumulative_union_probabilistic_probabilistic cumulative_union_sparse_full_representation cumulative_union_sparse_promotion
                        cumulative_union_sparse_sparse disable_hashagg equal explicit_thresh hash hash_any meta_func murmur_bigint murmur_bytea nosparse notequal scalar_oob storedproc
                        transaction typmod typmod_insert union_op"""
    self.setup_schedule_tests(schedule_tests.split())

    # copy sql update files into root repo dir with preprocessor options
    sql_update_path = os.path.join(repo_path, 'update')
    with cd(repo_path):
        for sql_update_file in listdir(sql_update_path):
            run('cpp -undef -w -P -imacros $({}/bin/pg_config --includedir-server)/pg_config.h {}/{} > {}'.format(
                config.PG_LATEST, sql_update_path, sql_update_file, sql_update_file))

def before_regression_topn(topn_task):    
    repo_path = InstallExtensionTask.repo_path_for_url(topn_task.repo_url)

    # set schedule tests
    schedule_tests = 'add_agg union_agg char_tests null_tests add_union_tests copy_data customer_reviews_query join_tests'
    self.setup_schedule_tests(schedule_tests.split())

    # copy sql update files into root repo dir with preprocessor options
    sql_update_path = os.path.join(repo_path, 'update')
    with cd(repo_path):
        for sql_update_file in listdir(sql_update_path):
            run('cpp -undef -w -P -imacros $({}/bin/pg_config --includedir-server)/pg_config.h {}/{} > {}'.format(
                config.PG_LATEST, sql_update_path, sql_update_file, sql_update_file))
    
    # download and unzip input csv file
    data_path = os.path.join(repo_path, 'data')
    with cd(data_path):
        run('curl -L http://examples.citusdata.com/customer_reviews_1998.csv.gz > customer_reviews_1998.csv.gz')
        run('gzip -d customer_reviews_1998.csv')

def before_regression_tdigest(tdigest_task):
    repo_path = InstallExtensionTask.repo_path_for_url(tdigest_task.repo_url)
    self.test_input_dir = os.path.join(repo_path, 'test')

    # set schedule tests
    schedule_tests = 'basic cast conversions incremental parallel_query value_count_api trimmed_aggregates'
    self.setup_schedule_tests(schedule_tests.split())

def add_cstore_to_shared_preload_libraries():
    conf = '{}/data/postgresql.conf'.format(config.PG_LATEST)

    existing_line = run('grep "^shared_preload_libraries" {}'.format(conf))

    if not existing_line or 'citus' not in existing_line:
        abort('Cannot add cstore before citus has been added')

    if 'cstore' in existing_line:
        return

    # append cstore to the line
    regexp = "^shared_preload_libraries\s*=\s*'\(.*\)'$"
    replacement = "shared_preload_libraries='\\1,cstore_fdw'"
    run('sed -i -e "s/{}/{}/" {}'.format(regexp, replacement, conf))

    execute(pg.restart)

cstore = InstallExtensionTask(
    task_name='cstore',
    doc='Adds the cstore extension to the instance in pg-latest',
    repo_url='https://github.com/citusdata/cstore_fdw.git',
    before_run_hook=lambda: sudo('yum install -q -y protobuf-c-devel'),
    post_install_hook=add_cstore_to_shared_preload_libraries,
)

shard_rebalancer = InstallExtensionTask(
    task_name='shard_rebalancer',
    doc='Adds the shard rebalancer extension to pg-latest (requires enterprise)',
    repo_url='git@github.com:citusdata/shard_rebalancer.git',
)

@task
@roles('master')
def tpch(**kwargs):
    'Generates and loads tpc-h data into the instance at pg-latest'
    prefix.check_for_pg_latest()

    psql = '{}/bin/psql'.format(config.PG_LATEST)

    connectionURI = kwargs.get('connectionURI', kwargs.get('connectionURI', ''))
    scale = kwargs.get('scale-factor', kwargs.get('scale_factor', 10))
    partition_type = kwargs.get('partition-type', kwargs.get('partition_type', 'default'))

    # generate tpc-h data
    tpch_path = '{}/tpch_2_13_0'.format(config.TESTS_REPO)
    with cd(tpch_path):
        run('make')
        run('SCALE_FACTOR={} CHUNKS="o 24 c 4 P 1 S 4 s 1" sh generate2.sh'.format(scale))

        # clear old tables
        run('{} {} -f drop_tables.sql'.format(psql, connectionURI))

        # create the tpc-h tables
        if partition_type == 'default':
            run('{} {} -f tpch_create_tables.ddl'.format(psql, connectionURI))
        elif partition_type == 'hash':
            run('{} {} -f tpch_create_hash_partitioned_tables.ddl'.format(psql, connectionURI))
        elif partition_type == 'append':
            run('{} {} -f tpch_create_append_partitioned_tables.ddl'.format(psql, connectionURI))

        # stage tpc-h data
        for segment in run('find {} -name \'*.tbl*\''.format(tpch_path)).splitlines():
            table_name = os.path.basename(segment).split('.')[0]
            run('''{} {} -c "\COPY {} FROM '{}' WITH DELIMITER '|'"'''.format(psql, connectionURI, table_name, segment))

        run('{} {} -f warm_up_cache.sql'.format(psql, connectionURI))

@task
@roles('master')
def jdbc():
    'Adds everything required to test out the jdbc connecter'
    sudo('yum install -q -y java-1.6.0-openjdk-devel') # we only need java on the master

@task
@roles('master')
def coordinator_to_metadata():
    local_ip = utils.get_local_ip()
    utils.psql("SELECT master_add_node('{}', {}, groupid => 0);".format(local_ip, config.PORT))

@task
@roles('master')
def shards_on_coordinator():
    local_ip = utils.get_local_ip()
    utils.psql("SELECT 1 FROM master_set_node_property('{}', {}, 'shouldhaveshards', true);"
        .format(local_ip, config.PORT))    