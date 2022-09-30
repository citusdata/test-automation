import os.path

from fabric.api import task, cd, path, run, roles, sudo, abort, execute
from fabric.tasks import Task
from fabric.context_managers import settings

import utils
import config
import prefix
import pg

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
        self.__doc__ = ""
        self.contrib = False
        self.repo_url = ""
        self.default_git_ref = ""
        self.preload = False
        self.configure = False
        self.relative_test_path = ""

    def parse_from_config(self, config_parser):
        extension_name = self.name

        doc = config_parser.get(extension_name, 'doc')
        contrib = eval(config_parser.get(extension_name, 'contrib'))
        preload = eval(config_parser.get(extension_name, 'preload'))
        configure = eval(config_parser.get(extension_name, 'configure'))

        repo_url = ''
        default_git_ref = ''
        if not contrib:
            repo_url = config_parser.get(extension_name, 'repo_url')
            default_git_ref = config_parser.get(extension_name, 'default_git_ref')

        relative_test_path = config_parser.get(extension_name, 'relative_test_path')

        self.doc = doc
        self.contrib = contrib
        self.repo_url = repo_url
        self.default_git_ref = default_git_ref
        self.preload = preload
        self.configure = configure
        self.relative_test_path = relative_test_path

class ExtensionTest:
    '''
    A class to represent extension test case
    '''

    def __init__(self, test_name, extension):
        self.test_name = test_name  # the name of the task (fab [xxx])
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

        extension_path = ''
        if self.extension.contrib:
            extension_path = contrib_path_for_extension(self.extension.name)
        else:
            extension_path = extension_path_for_url(self.extension.contrib, self.extension.repo_url)
        self.test_path = os.path.join(extension_path, self.extension.relative_test_path)

    def get_install_tasks(self):
        extension_install_tasks = []
        for dept_ext in self.dep_exts:
            extension_install_task = InstallExtensionTask(dept_ext)
            extension_install_tasks.append(extension_install_task)
        return extension_install_tasks

    def get_configure_task(self):
        return ConfigureExtensionTest(self.dep_exts, self.conf_lines)

    def load_depended_extensions(self):
        # add --load-extension=deps to REGRESS_OPTS in Makefile
        with cd(self.test_path):
            for dep_ext in self.dep_exts:
                if dep_ext.preload:
                    run("echo 'REGRESS_OPTS := $(REGRESS_OPTS) --load-extension={}' >> Makefile".format(dep_ext.name))

    def regress(self):
        # force drop contrib_regression or regression dbs if exists, some backend still use db, so drop db not works
        utils.psql("DROP DATABASE IF EXISTS contrib_regression, regression WITH (FORCE);")

        # create result folder if not exists
        utils.mkdir_if_not_exists(config.RESULTS_DIRECTORY)

        # load depended extensions
        self.load_depended_extensions()

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
            extension_regression_diff = config.REGRESSION_DIFFS_FILE + '_{}_'.format(self.test_name) + self.extension.name
            with cd(config.RESULTS_DIRECTORY):
                run('mv {} {}'.format(regression_diffs_path, extension_regression_diff))


class InstallExtensionTask(Task):
    '''
    A class which has all the boilerplate for building and installing extensions.
    '''

    def __init__(self, extension, **kwargs):
        self.name = extension.name  # the name of the task (fab [xxx])
        self.__doc__ = extension.doc  # the description which fab --list will list
        self.contrib = extension.contrib
        self.repo_url = extension.repo_url
        self.default_git_ref = extension.default_git_ref
        self.preload = extension.preload
        self.configure = extension.configure
        self.before_run_hook = kwargs.get('before_run_hook', None)
        self.post_install_hook = kwargs.get('post_install_hook', None)

        super(InstallExtensionTask, self).__init__()


    def run(self, *args):
        if self.before_run_hook:
            self.before_run_hook()

        extension_path = ''
        if self.contrib:
            extension_path = contrib_path_for_extension(self.name)
        else:
            extension_path = extension_path_for_url(self.contrib, self.repo_url)

        if not contrib: # contrib extensions are already installed
            prefix.check_for_pg_latest()  # make sure we're pointed at a real instance
            utils.add_github_to_known_hosts() # make sure ssh doesn't prompt

            if len(args) == 0:
                git_ref = self.default_git_ref
            else:
                git_ref = args[0]

            utils.rmdir(extension_path, force=True) # force because git write-protects files
            run('git clone -q {} {}'.format(self.repo_url, extension_path))

            with cd(extension_path), path('{}/bin'.format(config.PG_LATEST)):
                run('git checkout {}'.format(git_ref))
                core_count = run('cat /proc/cpuinfo | grep "core id" | wc -l')

                # run configure if extension has that step
                if self.configure:
                    run('PG_CONFIG={}/bin/pg_config ./configure'.format(config.PG_LATEST))

                # fallback to make install if make install-all does not exist
                run('make -s -j{core_count} install-all || make -s -j{core_count} install'.format(core_count=core_count))

        if self.post_install_hook:
            self.post_install_hook()


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
            # only select if dep extension is chosen to be preloaded
            preloaded_dep_names = [dep_ext.name for dep_ext in self.dep_exts if dep_ext.preload]
            preload_string = utils.get_preload_libs_string(preloaded_dep_names)
            
            # modify shared_preload_libraries according to dep order given in the regression test's config
            run('echo {} >> postgresql.conf'.format(preload_string))

            # add conf options given in the regression test's config
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