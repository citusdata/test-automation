import os.path
import re

from fabric.api import (
    env, cd, roles, task, parallel, execute, run,
    sudo, abort, local, lcd, path, put, warn
)
from fabric.decorators import runs_once
from fabric.contrib.files import append, exists

env.roledefs = {
    'master': ['localhost'],
    'workers': [ip.strip() for ip in open('worker-instances')],
}
env.roles = ['master', 'workers']
env.forward_agent = True # So remote machines can checkout private git repos

paths = {
    'tests-repo': '/home/ec2-user/test-automation',
    'citus-repo': '/home/ec2-user/citus',
    'enterprise-repo': '/home/ec2-user/citus-enterprise',
    'session-repo': '/home/ec2-user/session-analytics',
    'hll-repo': '/home/ec2-user/hll',
    'pg-latest': '/home/ec2-user/pg-latest',
    'pg-source-balls': '/home/ec2-user/postgres-source',
}

config = {
    # just a default, change it with the "citus" task
    'citus-git-ref': 'master',

     # change these with the "session_analytics" task
    'session-analytics-ref': 'master',
    'install-session-analytics': False,

    # toggle installation by using the "hll" task, always installs v2.10.0
    'hll-ref': 'v2.10.0',
    'install-hll': False,

    'pg-version': '9.6.1',
    'pg-configure-flags': [],
}

postgres_version_regex = '\d+\.\d+\.\d+$' # For example: 9.3.15

@task
@runs_once
def citus(*args):
    'Choose a citus version. For example: fab citus:v6.0.1 basic_testing (defaults to master)'

    # Do a local checkout to make sure this is a valid ref
    # (so we error as fast as possible)

    if len(args) != 1:
        abort('You must provide a single argument, with a command such as "citus:v6.0.1"')
    git_ref = args[0]

    path = paths['citus-repo']
    local('rm -rf {} || true'.format(path))
    local('git clone -q https://github.com/citusdata/citus.git {}'.format(path))
    with lcd(path):
        local('git checkout {}'.format(git_ref))
    local('rm -rf {} || true'.format(path))

    config['citus-git-ref'] = git_ref

@task
@runs_once
def postgres(*args):
    'Choose a postgres version. For example: fab postgres:9.6.1 basic_testing'

    if len(args) != 1:
        abort('You must provide a single argument. For example: "postgres:9.6.1"')
    version = args[0]
    if not re.match(postgres_version_regex, version):
        abort('"{}" is not a valid postgres version. Enter something like "9.6.1"'.format(version))

    config['pg-version'] = version
    download_pg() # Check that this doesn't 404

@task
@runs_once
def session_analytics(*args):
    'Install session analytics. Example: fab session_analytics:v1.0.0-rc.1 basic_testing [defaults to master]'

    if len(args) == 0:
        git_ref = 'master'
    else:
        git_ref = args[0]

    # confirm that the provided git-ref is legit
    path = paths['session-repo']
    local('rm -rf {} || true'.format(path))
    local('git clone -q git@github.com:citusdata/session_analytics.git {}'.format(path))
    with lcd(path):
        local('git checkout {}'.format(git_ref))
    local('rm -rf {} || true'.format(path))

    config['session-analytics-ref'] = git_ref
    config['install-session-analytics'] = True

@task
@runs_once
def asserts(*args):
    'Enable asserts in pg (and therefore citus)'
    config['pg-configure-flags'].append('--enable-cassert')

@task
@runs_once
def debug_mode(*args):
    '''ps's configure is passed: '--enable-debug --enable-cassert CFLAGS="-ggdb -Og -g3 -fno-omit-frame-pointer"' '''
    config['pg-configure-flags'].append('--enable-debug --enable-cassert CFLAGS="-ggdb -Og -g3 -fno-omit-frame-pointer"')

@task
@runs_once
def hll():
    'Marks hll for installation.'
    config['install-hll'] = True

@task
@runs_once
def basic_testing():
    'Sets up a no-frills Postgres+Citus cluster'
    prefix = '/home/ec2-user/pg-961'

    # use sequential executes to make sure all nodes are setup before we
    # attempt to call master_add_node (common_setup should be run on all nodes before
    # add_workers runs on master)

    execute(common_setup, prefix)
    execute(add_workers, prefix)
    print('You can now connect by running "{}/bin/psql"'.format(prefix))

@task
@runs_once
def tpch():
    'Just like basic_testing, but also includes some files useful for tpc-h'
    prefix = '/home/ec2-user/tpch'

    execute(common_setup, prefix)
    execute(add_workers, prefix)
    execute(tpch_setup, prefix)
    print('You can now connect by running "{}/bin/psql"'.format(prefix))
    print('The tpc-h scripts are at ""')

@task
@runs_once
def valgrind():
    'Just like basic_testing, but adds --enable-debug flag and installs valgrind'
    prefix = '/home/ec2-user/valgrind'

    # we do this dance so valgrind is installed on every node, not just the master
    def install_valgrind():
        sudo('yum install -q -y valgrind')
    execute(install_valgrind)

    config['pg-configure-flags'].append('--enable-debug')

    execute(common_setup, prefix)
    execute(add_workers, prefix)

@parallel
def common_setup(prefix):
    cleanup(prefix)
    redhat_install_packages()
    build_postgres(prefix)
    build_citus(prefix)
    create_database(prefix)
    start_database(prefix)
    setup_database(prefix)

def cleanup(prefix):
    run('pkill postgres || true')
    run('rm -r {} || true'.format(prefix))

@roles('master')
def tpch_setup(prefix):
    # generate tpc-h data
    tpch_path = '{}/tpch_2_13_0'.format(paths['tests-repo'])
    with cd(tpch_path):
        run('make')
        run('SCALE_FACTOR=10 CHUNKS="o 24 c 4 P 1 S 4 s 1" sh generate2.sh')

        # create the tpc-h tables
        run('{}/bin/psql -f tpch_create_tables.ddl'.format(prefix))

        # stage tpc-h data
        sed = r'''sed "s/\(.*\)\.tbl.*/\\\\COPY \1 FROM '\0' WITH DELIMITER '|'/"'''
        xargs = r'''xargs -d '\n' -L 1 -P 4 sh -c '{}/bin/psql -h localhost -c "$0"' '''.format(prefix)

        for segment in run('find {} -name \'*.tbl*\''.format(tpch_path)).splitlines():
            table_name = os.path.basename(segment).split('.')[0]
            run('''{}/bin/psql -c "COPY {} FROM '{}' WITH DELIMITER '|'"'''.format(prefix, table_name, segment))

@roles('master')
def add_workers(prefix):
    with cd(prefix):
        for ip in env.roledefs['workers']:
           command = 'SELECT master_add_node(\'{}\', 5432);'.format(ip)
           run('bin/psql -c "{}"'.format(command))

def redhat_install_packages():
    # you can detect amazon linux with /etc/issue and redhat with /etc/redhat-release
    sudo("yum groupinstall -q -y 'Development Tools'")
    sudo('yum install -q -y libxml2-devel libxslt-devel'
         ' openssl-devel pam-devel readline-devel git')

def build_postgres(prefix):
    'Installs postges'

    # Give the postgres source to the remote node
    sourceball_loc = download_pg()
    if env.host_string != 'localhost':
        put(local_path=sourceball_loc, remote_path=sourceball_loc)

    with cd(paths['pg-source-balls']):
        final_dir = os.path.basename(sourceball_loc).split('.tar.bz2')[0]
        # rm makes this idempotent, if not a bit inefficient
        run('rm -r {} || true'.format(final_dir))
        run('tar -xf {}.tar.bz2'.format(final_dir))

        with cd(final_dir):
            flags = ' '.join(config['pg-configure-flags'])
            run('./configure --prefix={} {}'.format(prefix, flags))
            run('make install')

    # Set the pg-latest link to the last-installed PostgreSQL
    run('rm -rf "{1}" && ln -s {0} {1}'.format(prefix, paths['pg-latest']))

def build_citus(prefix):
    repo = paths['citus-repo']
    run('rm -rf {} || true'.format(repo)) # -f because git write-protects files
    run('git clone -q https://github.com/citusdata/citus.git'.format(repo))
    with cd(repo):
        run('git checkout {}'.format(config['citus-git-ref']))
        run('PG_CONFIG={}/bin/pg_config ./configure'.format(prefix))
        run('make install')

def build_enterprise(prefix):
    add_github_to_known_hosts() # make sure ssh doesn't prompt
    repo = paths['enterprise-repo']
    run('rm -rf {} || true'.format(repo)) # -f because git write-protects files
    run('git clone -q git@github.com:citusdata/citus-enterprise.git'.format(repo))
    with cd(repo):
        run('git checkout {}'.format(config['citus-git-ref']))
        run('PG_CONFIG={}/bin/pg_config ./configure'.format(prefix))
        run('make install')

@task
def install_session_analytics(prefix):
    add_github_to_known_hosts() # make sure ssh doesn't prompt
    repo = paths['session-repo']

    run('rm -rf {} || true'.format(repo)) # -f because git write-protects files
    run('git clone -q git@github.com:citusdata/session_analytics.git {}'.format(repo))
    with cd(repo), path('{}/bin'.format(prefix)):
        run('git checkout {}'.format(config['session-analytics-ref']))
        run('make install')

def install_hll(prefix):
    repo = paths['hll-repo']
    url = 'https://github.com/aggregateknowledge/postgresql-hll.git'

    run('rm -rf {} || true'.format(repo))
    run('git clone -q {} {}'.format(url, repo))
    with cd(repo), path('{}/bin'.format(prefix)):
        run('git checkout {}'.format(config['hll-ref']))
        run('make install')

def create_database(prefix):
    with cd(prefix):
        run('bin/initdb -D data')
    with cd('{}/data'.format(prefix)):
        run('echo "shared_preload_libraries = \'citus\'" >> postgresql.conf')
        run('echo "max_prepared_transactions = 100" >> postgresql.conf')
        run('echo "listen_addresses = \'*\'" >> postgresql.conf')
        run('echo "host all all 10.192.0.0/16 trust" >> pg_hba.conf')

def start_database(prefix):
    with cd(prefix):
        # "set -m" makes sure postgres is spawned in a new process group and keeps running
        run('set -m; bin/pg_ctl -D data -l logfile start')

def setup_database(prefix):
    with cd(prefix):
        run('bin/createdb $(whoami)')
        run('bin/psql -c "CREATE EXTENSION citus;"')
        if config['install-session-analytics']:
            run('bin/psql -c "CREATE EXTENSION session_analytics;"')
        if config['install-hll']:
            run('bin/psql -c "CREATE EXTENSION hll')

def add_github_to_known_hosts():
    'Removes prompts from github checkouts asking whether you want to trust the remote'
    key = 'github.com ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ=='
    append('/home/ec2-user/.ssh/known_hosts', key)

def download_pg():
    "Idempotent, does not download if file already exists. Returns the file's location"
    version = config['pg-version']
    url = pg_url_for_version(version)

    target_dir = paths['pg-source-balls']
    run('mkdir -p {}'.format(target_dir))

    target_file = '{}/{}'.format(target_dir, os.path.basename(url))

    if exists(target_file):
        return target_file

    run('wget -O {} --no-verbose {}'.format(target_file, url))
    return target_file

def pg_url_for_version(version):
    assert re.match(postgres_version_regex, version) is not None
    return 'https://ftp.postgresql.org/pub/source/v{0}/postgresql-{0}.tar.bz2'.format(version)
