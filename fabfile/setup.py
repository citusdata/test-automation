import os.path

from fabric.api import (
    env, cd, roles, task, parallel, execute, run,
    sudo, abort, local, lcd, path, put, warn
)
from fabric.decorators import runs_once
from fabric.contrib.files import append, exists

import utils
import config
import pg
import add

__all__ = ["basic_testing", "tpch", "valgrind"]

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

@task
@runs_once
def tpch():
    'Just like basic_testing, but also includes some files useful for tpc-h'
    prefix = '/home/ec2-user/tpch'

    execute(common_setup, prefix)
    execute(add_workers, prefix)
    execute(add.tpch)
    print('You can now connect by running psql')

@task
@runs_once
def valgrind():
    'Just like basic_testing, but adds --enable-debug flag and installs valgrind'
    prefix = '/home/ec2-user/valgrind'

    # we do this dance so valgrind is installed on every node, not just the master
    def install_valgrind():
        sudo('yum install -q -y valgrind')
    execute(install_valgrind)

    config.settings['pg-configure-flags'].append('--enable-debug')

    execute(common_setup, prefix)
    execute(add_workers, prefix)

@parallel
def common_setup(prefix):
    run('pkill postgres || true')
    run('rm -r {} || true'.format(prefix))

    redhat_install_packages()
    build_postgres(prefix)
    build_citus(prefix)
    create_database(prefix)
    pg.start()
    with cd(prefix):
        run('bin/createdb $(whoami)')
        run('bin/psql -c "CREATE EXTENSION citus;"')

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
    sourceball_loc = utils.download_pg()
    if env.host_string != 'localhost':
        put(local_path=sourceball_loc, remote_path=sourceball_loc)

    with cd(config.paths['pg-source-balls']):
        final_dir = os.path.basename(sourceball_loc).split('.tar.bz2')[0]
        # rm makes this idempotent, if not a bit inefficient
        run('rm -r {} || true'.format(final_dir))
        run('tar -xf {}.tar.bz2'.format(final_dir))

        with cd(final_dir):
            flags = ' '.join(config.settings['pg-configure-flags'])
            run('./configure --prefix={} {}'.format(prefix, flags))
            run('make install')

    # Set the pg-latest link to the last-installed PostgreSQL
    run('rm -rf "{1}" && ln -s {0} {1}'.format(prefix, config.paths['pg-latest']))

def build_citus(prefix):
    repo = config.paths['citus-repo']
    run('rm -rf {} || true'.format(repo)) # -f because git write-protects files
    run('git clone -q https://github.com/citusdata/citus.git'.format(repo))
    with cd(repo):
        run('git checkout {}'.format(config.settings['citus-git-ref']))
        run('PG_CONFIG={}/bin/pg_config ./configure'.format(prefix))
        run('make install')

def build_enterprise(prefix):
    add_github_to_known_hosts() # make sure ssh doesn't prompt
    repo = config.paths['enterprise-repo']
    run('rm -rf {} || true'.format(repo)) # -f because git write-protects files
    run('git clone -q git@github.com:citusdata/citus-enterprise.git'.format(repo))
    with cd(repo):
        run('git checkout {}'.format(config.settings['citus-git-ref']))
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
