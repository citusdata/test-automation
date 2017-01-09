import os.path

from fabric.api import task, cd, path, run, runs_once, roles, sudo, abort
from fabric.tasks import Task

import utils
import config
import prefix

__all__ = [
    'session_analytics', 'hll', 'cstore', 'tpch', 'jdbc', 'shard_rebalancer'
]

class InstallExtensionTask(Task):
    '''
    A class which has all the boilerplate for building and installing extensions.
    Instantiate it to make it show up in the list of tasks.

    Tasks created with this class accept a single parameter, the git revision to check out
    and build. e.x. `fab add.shard_rebalancer:master`. Will default to using 'master'
    unless you specify otherwise by passing 'default_git_ref'.

    If you don't specify `extension_name` (used to call CREATE EXTENSION) it defaults to
    using the name of the task.
    '''

    def __init__(self, task_name, doc, repo_url, **kwargs):
        self.name = task_name  # the name of the task (fab [xxx])
        self.__doc__ = doc  # the description which fab --list will list
        self.repo_url = repo_url

        self.extension_name = kwargs.get('extension_name', self.name)
        self.default_git_ref = kwargs.get('default_git_ref', 'master')
        self.before_run_hook = kwargs.get('before_run_hook', None)
        self.post_install_hook = kwargs.get('post_install_hook', None)

        super(InstallExtensionTask, self).__init__()

    @staticmethod
    def repo_path_for_url(repo_url):
        repo_name = run('basename {}'.format(repo_url))
        repo_name = repo_name.split('.')[0] # chop off the '.git' at the end
        return os.path.join(config.paths['code-directory'], repo_name)

    def run(self, *args):
        if self.before_run_hook:
            self.before_run_hook()

        prefix.check_for_pg_latest()  # make sure we're pointed at a real instance
        utils.add_github_to_known_hosts() # make sure ssh doesn't prompt

        repo = self.repo_path_for_url(self.repo_url)

        if len(args) == 0:
            git_ref = self.default_git_ref
        else:
            git_ref = args[0]

        utils.rmdir(repo, force=True) # force because git write-protects files
        run('git clone -q {} {}'.format(self.repo_url, repo))

        with cd(repo), path('{}/bin'.format(config.paths['pg-latest'])):
            run('git checkout {}'.format(git_ref))
            run('make install')

        if self.post_install_hook:
            self.post_install_hook()

        # TODO: What if the server isn't running?
        utils.psql('CREATE EXTENSION {} CASCADE;'.format(self.extension_name))

session_analytics = InstallExtensionTask(
    task_name='session_analytics',
    doc='Adds the session analytics extension to the instance in pg-latest',
    repo_url='git@github.com:citusdata/session_analytics.git',
)

hll = InstallExtensionTask(
    task_name='hll',
    doc='Adds the hll extension to the instance in pg-latest',
    repo_url='https://github.com/aggregateknowledge/postgresql-hll.git',
    default_git_ref='v2.10.0',
)

def add_cstore_to_shared_preload_libraries():
    conf = '{}/data/postgresql.conf'.format(config.paths['pg-latest'])

    existing_line = run('grep "^shared_preload_libraries" {}'.format(conf))

    if not existing_line or 'citus' not in existing_line:
        abort('Cannot add cstore before citus has been added')

    if 'cstore' in existing_line:
        return

    # append cstore to the line
    regexp = "^shared_preload_libraries\s*=\s*'\(.*\)'$"
    replacement = "shared_preload_libraries='\\1,cstore'"
    run('sed -i -e "s/{}/{}/" {}'.format(regexp, replacement, conf))

# TODO: It should also restart the server
cstore = InstallExtensionTask(
    task_name='cstore',
    doc='Adds the cstore extension to the instance in pg-latest',
    repo_url='https://github.com/citusdata/cstore_fdw.git',
    extension_name='cstore_fdw',
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

    psql = '{}/bin/psql'.format(config.paths['pg-latest'])

    scale = kwargs.get('scale-factor', 10)

    # generate tpc-h data
    tpch_path = '{}/tpch_2_13_0'.format(config.paths['tests-repo'])
    with cd(tpch_path):
        run('make')
        run('SCALE_FACTOR={} CHUNKS="o 24 c 4 P 1 S 4 s 1" sh generate2.sh'.format(scale))

        # create the tpc-h tables
        run('{} -f tpch_create_tables.ddl'.format(psql))

        # stage tpc-h data
        sed = r'''sed "s/\(.*\)\.tbl.*/\\\\COPY \1 FROM '\0' WITH DELIMITER '|'/"'''
        xargs = r'''xargs -d '\n' -L 1 -P 4 sh -c '{} -h localhost -c "$0"' '''.format(psql)

        for segment in run('find {} -name \'*.tbl*\''.format(tpch_path)).splitlines():
            table_name = os.path.basename(segment).split('.')[0]
            run('''{} -c "COPY {} FROM '{}' WITH DELIMITER '|'"'''.format(psql, table_name, segment))

@task
@roles('master')
def jdbc():
    'Adds everything required to test out the jdbc connecter'
    sudo('yum install -q -y java-1.6.0-openjdk-devel') # we only need java on the master
