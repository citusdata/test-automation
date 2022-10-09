import os.path

from fabric.api import task, cd, path, run, roles, sudo, abort, execute
from fabric.tasks import Task
from fabric.context_managers import settings

import utils
import config
import prefix
import pg
import extension_hooks

__all__ = [
    'tpch', 'jdbc', 'coordinator_to_metadata', 'shards_on_coordinator'
]

def extension_path_for_url(repo_url):
    repo_name = run('basename {}'.format(repo_url))
    repo_name = repo_name.split('.')[0] # chop off the '.git' at the end
    return os.path.join(config.CODE_DIRECTORY, repo_name)

def contrib_path_for_extension(extension_name):
    pg_contrib_dir = utils.pg_contrib_dir()
    return os.path.join(pg_contrib_dir, extension_name)

class Extension:
    '''
    A class to represent extensions to be used in extension tasks
    '''

    def __init__(self, name):
        self.name = name
        self.contrib = False
        self.repo_url = ""
        self.git_ref = ""
        self.preload = False
        self.create = False
        self.configure = False
        self.relative_test_path = ""
        self.conf_lines = []
        self.post_create_hook = None

    def parse_from_config(self, config_parser):
        extension_name = self.name

        contrib = eval(config_parser.get(extension_name, 'contrib'))
        preload = eval(config_parser.get(extension_name, 'preload'))
        create = eval(config_parser.get(extension_name, 'create'))
        configure = eval(config_parser.get(extension_name, 'configure'))

        repo_url = ''
        git_ref = ''
        if not contrib:
            repo_url = config_parser.get(extension_name, 'repo_url')
            git_ref = config_parser.get(extension_name, 'git_ref')

        relative_test_path = config_parser.get(extension_name, 'relative_test_path')

        conf_lines = []
        if config_parser.has_option(extension_name, 'conf_string'):
            conf_lines = eval(config_parser.get(extension_name, 'conf_string')).split()

        post_create_hook = None
        if config_parser.has_option(extension_name, 'post_create_hook'):
            post_create_hook_name = config_parser.get(extension_name, 'post_create_hook')
            post_create_hook = getattr(extension_hooks, post_create_hook_name)

        self.contrib = contrib
        self.repo_url = repo_url
        self.git_ref = git_ref
        self.preload = preload
        self.create = create
        self.configure = configure
        self.relative_test_path = relative_test_path
        self.conf_lines = conf_lines
        self.post_create_hook = post_create_hook

class ExtensionTest:
    '''
    A class to represent extension test case
    '''

    def __init__(self, test_name, extension):
        self.test_name = test_name
        self.extension = extension
        self.conf_lines = []
        self.test_command = ""
        self.dep_exts = []

    def parse_from_config(self, config_parser):
        test_name = self.test_name

        dep_order = config_parser.get(test_name, 'dep_order').split(',')
        for dep in dep_order:
            dep_ext = Extension(dep)
            dep_ext.parse_from_config(config_parser)
            self.dep_exts.append(dep_ext)

        self.test_command = config_parser.get(test_name, 'test_command')

        if config_parser.has_option(test_name, 'conf_string'):
            self.conf_lines = eval(config_parser.get(test_name, 'conf_string')).split()

    def get_install_tasks(self):
        extension_install_tasks = []
        for dept_ext in self.dep_exts:
            extension_install_task = InstallExtensionTask(dept_ext)
            extension_install_tasks.append(extension_install_task)
        return extension_install_tasks

    def get_configure_task(self):
        return ConfigureExtensionTest(self.dep_exts, self.conf_lines)

    def use_existing_database(self):
        # pg_regress will not drop and recreate database for testing. It will use the pguser default db which is already setup.
        with cd(self.test_path):
            run("echo 'REGRESS_OPTS := $(REGRESS_OPTS) --use-existing --dbname=pguser --user=pguser' >> Makefile")

    def set_test_path(self):
        extension_path = ''
        if self.extension.contrib:
            extension_path = contrib_path_for_extension(self.extension.name)
        else:
            extension_path = extension_path_for_url(self.extension.repo_url)
        self.test_path = os.path.join(extension_path, self.extension.relative_test_path)

    def regress(self):
        # create result folder if not exists
        utils.mkdir_if_not_exists(config.RESULTS_DIRECTORY)

        # set test dir so that next steps can use it
        self.set_test_path()

        # some pg_regress options to use existing database instead of recreating it
        self.use_existing_database()

        # run tests with warn_only option to not exit in case of a test failure in the extension,
        # because we want to run regression tests for other extensions too.
        with settings(warn_only=True):
            with cd(self.test_path):
                run(self.test_command)

        # rename regression.diffs, if exists, so that extension's diff file does not conflict with others'
        self.rename_regression_diff()

    def rename_regression_diff(self):
        regression_diffs_path = os.path.join(self.test_path, config.REGRESSION_DIFFS_FILE)
        if os.path.isfile(regression_diffs_path):
            extension_regression_diff = config.REGRESSION_DIFFS_FILE + '_{}_{}_'.format(config.PG_VERSION, self.test_name) + self.extension.name
            with cd(config.RESULTS_DIRECTORY):
                run('mv {} {}'.format(regression_diffs_path, extension_regression_diff))


class InstallExtensionTask(Task):
    '''
    A class which has all the boilerplate for building and installing extensions.
    '''

    def __init__(self, extension, **kwargs):
        self.name = extension.name
        self.contrib = extension.contrib
        self.repo_url = extension.repo_url
        self.git_ref = extension.git_ref
        self.preload = extension.preload
        self.create = extension.create
        self.configure = extension.configure
        self.post_create_hook = extension.post_create_hook

        super(InstallExtensionTask, self).__init__()

    def create_extension(self):
        if self.create:
            utils.psql('CREATE EXTENSION "{}";'.format(self.name))
        if self.post_create_hook:
            self.post_create_hook()

    def get_unique_package_name(self):
        if self.contrib:
            return "{}-{}".format(self.name, config.PG_VERSION)
        else:
            return "{}-{}-{}".format(self.name, self.git_ref, config.PG_VERSION)

    def run(self):
        extension_path = ''
        if self.contrib:
            extension_path = contrib_path_for_extension(self.name)
        else:
            extension_path = extension_path_for_url(self.repo_url)

        if not self.contrib: # contrib extensions are already installed
            prefix.check_for_pg_latest()  # make sure we're pointed at a real instance
            utils.add_github_to_known_hosts() # make sure ssh doesn't prompt

            utils.rmdir(extension_path, force=True) # force because git write-protects files
            run('git clone -q {} {}'.format(self.repo_url, extension_path))

            with cd(extension_path), path('{}/bin'.format(config.PG_LATEST)):
                run('git checkout {}'.format(self.git_ref))
                core_count = utils.get_core_count()

                # run configure if extension has that step
                if self.configure:
                    run('PG_CONFIG={}/bin/pg_config ./configure'.format(config.PG_LATEST))

                # fallback to make install if make install-all does not exist
                run('make -s -j{core_count} install-all || make -s -j{core_count} install'.format(core_count=core_count))


class ConfigureExtensionTest:
    '''
    A class which has all the boilerplate for configuring extensions for the extension test.
    '''

    def __init__(self, dep_exts, conf_lines):
        self.dep_exts = dep_exts
        self.conf_lines = conf_lines

    def configure(self):
        pg_latest = config.PG_LATEST
        with cd('{}/data'.format(pg_latest)):
            # add general conf options for the extension if it has any
            for dep_ext in self.dep_exts:
                for option in dep_ext.conf_lines:
                    run('echo {} >> postgresql.conf'.format(option))

            # only select if dep extension is chosen to be preloaded
            preloaded_dep_names = [dep_ext.name for dep_ext in self.dep_exts if dep_ext.preload]
            preload_string = utils.get_preload_libs_string(preloaded_dep_names)

            # modify shared_preload_libraries according to dep order given in the regression test's config
            run('echo "{}" >> postgresql.conf'.format(preload_string))

            # add conf options given in the regression test's config (maybe override general settings for the extensions)
            for option in self.conf_lines:
                run('echo {} >> postgresql.conf'.format(option))


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
    tpch_path = '{}/tpch_2_13_0'.format(config.TEST_REPO)
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
