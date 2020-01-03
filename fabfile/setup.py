'''
Tasks which are aimed at facilitating specific components of our release testing.

Ideally you can run `fab setup.tpch`, for example, and immdiately start running tpc-h
queries.
'''
import os.path
import os
import math

from fabric.api import (
    env, cd, hide, roles, task, parallel, execute, run,
    sudo, abort, local, lcd, path, put, warn
)
from fabric.decorators import runs_once
from fabric.contrib.files import exists

import utils
import config
import ConfigParser
import pg
import add
import use
import prefix

__all__ = ["basic_testing", "tpch", "valgrind", "enterprise", "hammerdb"]

@task
@roles('master')
def basic_testing():
    'Sets up a no-frills Postgres+Citus cluster'
    execute(prefix.ensure_pg_latest_exists, default=config.CITUS_INSTALLATION)

    execute(common_setup, build_citus)
    execute(add_workers)

@task
@roles('master')
def tpch():
    'Just like basic_testing, but also includes some files useful for tpc-h'
    execute(prefix.ensure_pg_latest_exists, default=config.CITUS_INSTALLATION)

    execute(common_setup, build_citus)
    execute(add_workers)
    execute(add.tpch)

@task
def valgrind():
    'Just like basic_testing, but adds --enable-debug flag and installs valgrind'
    execute(prefix.ensure_pg_latest_exists, default=config.CITUS_INSTALLATION)

    # we do this execute dance so valgrind is installed on every node, not just the master
    def install_valgrind():
        sudo('yum install -q -y valgrind')
    execute(install_valgrind)

    config.PG_CONFIGURE_FLAGS.append('--enable-debug')

    execute(common_setup, build_citus)
    execute(add_workers)    

@task
def enterprise():
    'Installs the enterprise version of Citus'
    execute(prefix.ensure_pg_latest_exists, default=config.CITUS_INSTALLATION)

    execute(common_setup, build_enterprise)
    execute(add_workers)

@task
@roles('master')
def hammerdb(config_file='hammerdb.ini', driver_ip=''):

    config_parser = ConfigParser.ConfigParser()

    config_path = os.path.join(config.HOME_DIR, "test-automation/fabfile/hammerdb_confs", config_file)
    config_parser.read(config_path)

    use_enterprise = config_parser.get('DEFAULT', 'use_enterprise')
    pg_version, citus_version = eval(config_parser.get('DEFAULT', 'postgres_citus_version'))
    # create database for the given citus and pg versions
    if use_enterprise == 'on':
        execute(use.postgres, pg_version)
        execute(use.enterprise, citus_version)
        enterprise()
    else:
        execute(use.postgres, pg_version)
        execute(use.citus, citus_version)
        basic_testing()

    execute(set_hammerdb_config, config_parser, driver_ip)

@task
def set_hammerdb_config(config_parser, driver_ip):
    total_mem_in_gb = total_memory_in_gb()
    mem_mib = total_mem_in_gb * 1024

    shared_buffers_mib = int(0.25 * mem_mib)
    effective_cache_size_mib = int(mem_mib - shared_buffers_mib)
    maintenance_work_mem_mib = int(82.5 * math.log(total_mem_in_gb, 10) + 40)
    work_mem_mib = int(30 * math.log(total_mem_in_gb, 10) + 10)

    pg.set_config_str("shared_buffers = '{}MB'".format(shared_buffers_mib))
    pg.set_config_str("effective_cache_size = '{}MB'".format(effective_cache_size_mib))
    pg.set_config_str("maintenance_work_mem = '{}MB'".format(maintenance_work_mem_mib))
    pg.set_config_str("work_mem = '{}MB'".format(work_mem_mib))

    postgresql_conf_list = eval(config_parser.get('DEFAULT', 'postgresql_conf'))
    for postgresql_conf in postgresql_conf_list:
        pg.set_config_str(postgresql_conf)

    pg_latest = config.PG_LATEST
    with cd('{}/data'.format(pg_latest)):
        run('echo "host all all {}/16 trust" >> pg_hba.conf'.format(driver_ip))

    pg.restart()


def total_memory_in_gb():
    mem_bytes = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')  # e.g. 4015976448
    mem_gib = mem_bytes/(1024.**3)
    return mem_gib

@parallel
def common_setup(build_citus_func):
    with hide('stdout'):
        run('pkill postgres || true')

    prefix.check_for_pg_latest()
    # empty it but don't delete the link
    run('rm -r {}/* || true'.format(config.PG_LATEST))

    redhat_install_packages()
    build_postgres()
    build_citus_func()
    create_database()
    pg.start()

    pg_latest = config.PG_LATEST
    with cd(pg_latest):
        while getattr(run('bin/pg_isready'), 'return_code') != 0:
            print ('Waiting for database to be ready')

        run('bin/createdb $(whoami)')

    with hide('stdout'):
        utils.psql('CREATE EXTENSION citus;')

@roles('master')
def add_workers():
    with cd('{}/data'.format(config.PG_LATEST)):
        for ip in env.roledefs['workers']:
            with hide('stdout'):
                utils.psql('SELECT master_add_node(\'{}\', 5432);'.format(ip))
                run('echo "{} 5432" >> pg_worker_list.conf'.format(ip))

def redhat_install_packages():
    # you can detect amazon linux with /etc/issue and redhat with /etc/redhat-release
    with hide('stdout'):
        sudo("yum groupinstall -q -y 'Development Tools'")

    with hide('stdout'):
        sudo('yum install -q -y libxml2-devel libxslt-devel'
            ' openssl-devel pam-devel readline-devel libcurl-devel git')

def build_postgres():
    'Installs postges'

    # Give the postgres source to the remote nodes
    sourceball_loc = utils.download_pg()
    if env.host_string != 'localhost':
        put(local_path=sourceball_loc, remote_path=sourceball_loc)

    with cd(config.PG_SOURCE_BALLS):
        final_dir = os.path.basename(sourceball_loc).split('.tar.bz2')[0]
        # rm makes this idempotent, if not a bit inefficient

        utils.rmdir(final_dir)
        with hide('stdout'):
            run('tar -xf {}.tar.bz2'.format(final_dir))

        with cd(final_dir):
            pg_latest = config.PG_LATEST
            flags = ' '.join(config.PG_CONFIGURE_FLAGS)
            with hide('stdout'):
                run('./configure --prefix={} {}'.format(pg_latest, flags))

            core_count = run('cat /proc/cpuinfo | grep "core id" | wc -l')

            with hide('stdout'):
                run('make -s -j{} install'.format(core_count))

            with cd('contrib'), hide('stdout'):
                run('make -s install')

def build_citus():
    repo = config.CITUS_REPO
    utils.rmdir(repo, force=True) # force because git write-protects files
    run('git clone -q https://github.com/citusdata/citus.git {}'.format(repo))
    with cd(repo):
        git_ref = config.settings.get('citus-git-ref', 'master')
        run('git checkout {}'.format(git_ref))

        pg_latest = config.PG_LATEST
        with hide('stdout'):
            run('PG_CONFIG={}/bin/pg_config ./configure'.format(pg_latest))

        with hide('stdout', 'running'):
            core_count = run('cat /proc/cpuinfo | grep "core id" | wc -l')

        with hide('stdout'):
            run('make -s -j{} install'.format(core_count))

def build_enterprise():
    utils.add_github_to_known_hosts() # make sure ssh doesn't prompt
    repo = config.ENTERPRISE_REPO
    utils.rmdir(repo, force=True)
    run('git clone -q git@github.com:citusdata/citus-enterprise.git {}'.format(repo))
    with cd(repo):
        git_ref = config.settings.get('citus-git-ref', 'enterprise-master')
        run('git checkout {}'.format(git_ref))

        pg_latest = config.PG_LATEST
        with hide('stdout'):
            run('PG_CONFIG={}/bin/pg_config ./configure'.format(pg_latest))

        core_count = run('cat /proc/cpuinfo | grep "core id" | wc -l')

        with hide('stdout'):
            run('make -s -j{} install'.format(core_count))

def create_database():
    pg_latest = config.PG_LATEST
    with cd(pg_latest), hide('stdout'):
        run('bin/initdb -D data')
    with cd('{}/data'.format(pg_latest)):
        run('echo "shared_preload_libraries = \'citus\'" >> postgresql.conf')
        run('echo "max_prepared_transactions = 100" >> postgresql.conf')
        run('echo "listen_addresses = \'*\'" >> postgresql.conf')
        run('echo "wal_level = \'logical\'" >> postgresql.conf')
        run('echo "host all all 10.192.0.0/16 trust" >> pg_hba.conf')
