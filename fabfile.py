import tempfile
import os
import StringIO
import glob
import os.path

from fabric.api import (
    env, cd, roles, task, parallel, execute, run, sudo, abort, local, lcd
)
from fabric.decorators import runs_once

env.roledefs = {
    'master': ['localhost'],
    'workers': [ip.strip() for ip in open('worker-instances')],
}
env.roles = ['master', 'workers']

paths = {
    'tests-repo': '/home/ec2-user/test-automation',
    'citus-repo': '/home/ec2-user/citus',
    'session-repo': '/home/ec2-user/session-analytics',
    'pg-latest': '/home/ec2-user/pg-latest',
}

config = {
    'citus-git-ref': 'master',
    'install-session-analytics': False,
}

@task
@runs_once
def citus(*args):
    'Choose a citus version. For example: fab citus:v6.0.1 basic_testing'

    # Do a local checkout to make sure this is a valid ref
    # (so we error as fast as possible)

    if len(args) != 1:
        abort('You must provide a single argument, with a command such as "citus:feature/joins"')
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
def session_analytics(*args):
    'Install session analytics. Example: fab session_analytics:v1.0.0-rc.1 basic_testing [defaults to master]'

    if len(args) == 0:
        git_ref = 'master'
    else:
        git_ref = args[0]

    path = paths['session-repo']
    local('rm -rf {} || true'.format(path))
    local('git clone -q git@github.com:citusdata/session_analytics.git {}'.format(path))
    with lcd(path):
        local('git checkout {}'.format(git_ref))

    config['session-analytics'] = True

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

@parallel
def common_setup(prefix):
    cleanup(prefix)
    redhat_install_packages()
    build_postgres_96(prefix)
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

def postgres_95():
    'Installs postges 9.5 from source'

    # Fetched from: https://ftp.postgresql.org/pub/source/v9.5.5/postgresql-9.5.5.tar.bz2
    postgres_url = 'https://s3.eu-central-1.amazonaws.com/citus-tests/postgresql-9.5.5.tar.bz2'
    operations.get(postgres_url)

def build_postgres_96(prefix):
    'Installs postges 9.6 from source'
    # TODO: This might be more efficient if we download it locally and operations.put()
    # the file to the remote nodes

    # Fetched from https://ftp.postgresql.org/pub/source/v9.6.1/postgresql-9.6.1.tar.bz2
    postgres_url = 'https://s3.eu-central-1.amazonaws.com/citus-tests/postgresql-9.6.1.tar.bz2'

    # -N means we'll check timestamps before overwriting the file, more importantly it
    # means we won't save this file as postgresql-9.5.5.tar.bz2.1 if it already exists
    run('wget -N --no-verbose {}'.format(postgres_url))

    # rm makes this idempotent, if not a bit inefficient
    run('rm -r postgresql-9.6.1 || true')
    run('tar -xf postgresql-9.6.1.tar.bz2')
    with cd('postgresql-9.6.1'):
        run('./configure --prefix={}'.format(prefix))
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
