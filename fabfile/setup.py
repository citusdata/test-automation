'''
Tasks which are aimed at facilitating specific components of our release testing.

Ideally you can run `fab setup.tpch`, for example, and immdiately start running tpc-h
queries.
'''
import os.path

from fabric.api import (
    env, cd, roles, task, parallel, execute, run,
    sudo, abort, local, lcd, path, put, warn
)
from fabric.decorators import runs_once
from fabric.contrib.files import exists

import utils
import config
import pg
import add
import prefix

__all__ = ["basic_testing", "tpch", "valgrind", "enterprise"]

@task
@runs_once
def basic_testing():
    'Sets up a no-frills Postgres+Citus cluster'
    execute(prefix.ensure_pg_latest_exists, '/home/ec2-user/citus-installation')
    pg_latest = config.paths['pg-latest']

    # use sequential executes to make sure all nodes are setup before we
    # attempt to call master_add_node (common_setup should be run on all nodes before
    # add_workers runs on master)

    execute(common_setup, pg_latest, build_citus)
    execute(add_workers, pg_latest)

@task
@runs_once
def tpch():
    'Just like basic_testing, but also includes some files useful for tpc-h'
    prefix.ensure_pg_latest_exists('/home/ec2-user/citus-installation')
    pg_latest = config.paths['pg-latest']

    execute(common_setup, pg_latest, build_citus)
    execute(add_workers, pg_latest)
    execute(add.tpch)
    print('You can now connect by running psql')

@task
@runs_once
def valgrind():
    'Just like basic_testing, but adds --enable-debug flag and installs valgrind'
    prefix.ensure_pg_latest_exists('/home/ec2-user/citus-installation')
    pg_latest = config.paths['pg-latest']

    # we do this dance so valgrind is installed on every node, not just the master
    def install_valgrind():
        sudo('yum install -q -y valgrind')
    execute(install_valgrind)

    config.settings['pg-configure-flags'].append('--enable-debug')

    execute(common_setup, pg_latest, build_citus)
    execute(add_workers, pg_latest)

@task
@runs_once
def enterprise():
    'Installs the enterprise version of Citus'
    prefix.ensure_pg_latest_exists('/home/ec2-user/citus-installation')
    pg_latest = config.paths['pg-latest']

    # TODO: Add the ability to choose a branch
    config.settings['citus-git-ref'] = 'enterprise-master'

    execute(common_setup, pg_latest, build_enterprise)
    execute(add_workers, pg_latest)

@parallel
def common_setup(pg_latest, build_citus_func):
    run('pkill postgres || true')

    # empty it but don't delete the link
    if not exists(pg_latest):
        abort('Something went wrong, {} does not exist! It should be a link somewhere'.format(pg_latest))
    run('rm -r {}/ || true'.format(pg_latest))

    redhat_install_packages()
    build_postgres(pg_latest)
    build_citus_func(pg_latest)
    create_database(pg_latest)
    pg.start()
    with cd(pg_latest):
        run('bin/createdb $(whoami)')
        run('bin/psql -c "CREATE EXTENSION citus;"')

@roles('master')
def add_workers(pg_latest):
    with cd(pg_latest):
        for ip in env.roledefs['workers']:
           command = 'SELECT master_add_node(\'{}\', 5432);'.format(ip)
           run('bin/psql -c "{}"'.format(command))

def redhat_install_packages():
    # you can detect amazon linux with /etc/issue and redhat with /etc/redhat-release
    sudo("yum groupinstall -q -y 'Development Tools'")
    sudo('yum install -q -y libxml2-devel libxslt-devel'
         ' openssl-devel pam-devel readline-devel git')

def build_postgres(pg_latest):
    'Installs postges'

    # Give the postgres source to the remote node
    sourceball_loc = utils.download_pg()
    if env.host_string != 'localhost':
        put(local_path=sourceball_loc, remote_path=sourceball_loc)

    with cd(config.paths['pg-source-balls']):
        final_dir = os.path.basename(sourceball_loc).split('.tar.bz2')[0]
        # rm makes this idempotent, if not a bit inefficient
        utils.rmdir(final_dir)
        run('tar -xf {}.tar.bz2'.format(final_dir))

        with cd(final_dir):
            core_count = run('cat /proc/cpuinfo | grep "core id" | wc -l')
            flags = ' '.join(config.settings['pg-configure-flags'])
            run('./configure --prefix={} {}'.format(pg_latest, flags))
            run('make -j{} install'.format(core_count))

def build_citus(pg_latest):
    repo = config.paths['citus-repo']
    utils.rmdir(repo, force=True) # force because git write-protects files
    run('git clone -q https://github.com/citusdata/citus.git {}'.format(repo))
    with cd(repo):
        core_count = run('cat /proc/cpuinfo | grep "core id" | wc -l')
        run('git checkout {}'.format(config.settings['citus-git-ref']))
        run('PG_CONFIG={}/bin/pg_config ./configure'.format(pg_latest))
        run('make -j{} install'.format(core_count))

def build_enterprise(pg_latest):
    utils.add_github_to_known_hosts() # make sure ssh doesn't prompt
    repo = config.paths['enterprise-repo']
    utils.rmdir(repo, force=True)
    run('git clone -q git@github.com:citusdata/citus-enterprise.git {}'.format(repo))
    with cd(repo):
        run('git checkout {}'.format(config.settings['citus-git-ref']))
        run('PG_CONFIG={}/bin/pg_config ./configure'.format(pg_latest))
        run('make install')

def create_database(pg_latest):
    with cd(pg_latest):
        run('bin/initdb -D data')
    with cd('{}/data'.format(pg_latest)):
        run('echo "shared_preload_libraries = \'citus\'" >> postgresql.conf')
        run('echo "max_prepared_transactions = 100" >> postgresql.conf')
        run('echo "listen_addresses = \'*\'" >> postgresql.conf')
        run('echo "host all all 10.192.0.0/16 trust" >> pg_hba.conf')
