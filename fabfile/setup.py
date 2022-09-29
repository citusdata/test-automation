'''
Tasks which are aimed at facilitating specific components of our release testing.

Ideally you can run `fab setup.tpch`, for example, and immdiately start running tpc-h
queries.
'''
import os.path
import os
import math

from invoke import task
from invoke.exceptions import Exit
from patchwork.files import exists

import utils
import connection
import config
import configparser
import pg
import add
import use
import prefix
import use

__all__ = ["basic_testing", "tpch", "valgrind", "enterprise", "hammerdb"]

@task
def basic_testing(c, extension_install_tasks=[]):
    'Sets up a no-frills Postgres+Citus cluster'
    prefix.ensure_pg_latest_exists(c, default=config.CITUS_INSTALLATION)

    common_setup(c, build_citus, extension_install_tasks)
    add_workers(c)

@task
def tpch(c):
    'Just like basic_testing, but also includes some files useful for tpc-h'
    prefix.ensure_pg_latest_exists(c, default=config.CITUS_INSTALLATION)

    common_setup(c, build_citus)
    add_workers(c)
    add.tpch(c)

@task
def valgrind(c):
    # prepare yum install command
    install_required_packages_command = 'yum install -q -y ' + ' '.join(config.VALGRIND_REQUIRED_PACKAGES)

    # install libraries required for valgrind test
    c.sudo(install_required_packages_command)

    # create results directory to put resulting log files there
    # (for pushing them to results repository)
    utils.rmdir(c, config.RESULTS_DIRECTORY, force=True)
    utils.mkdir_if_not_exists(config.RESULTS_DIRECTORY)

    # set build citus function
    build_citus_func = config.settings[config.BUILD_CITUS_FUNC]
    prefix.ensure_pg_latest_exists(c, default=config.CITUS_INSTALLATION)
    common_setup(c, build_citus_func)

@task
def enterprise(c):
    'Installs the enterprise version of Citus'
    prefix.ensure_pg_latest_exists(c, default=config.CITUS_INSTALLATION)

    common_setup(c, build_enterprise)
    add_workers(c)

@task
def hammerdb(config_file='hammerdb.ini', driver_ip=''):
    config_parser = configparser.ConfigParser()

    config_path = os.path.join(config.HOME_DIR, "test-automation/fabfile/hammerdb_confs", config_file)
    config_parser.read(config_path)

    use_enterprise = config_parser.get('DEFAULT', 'use_enterprise')
    pg_version, citus_version = eval(config_parser.get('DEFAULT', 'postgres_citus_version'))
    # this should be run before any setup so that it sets the necessary fields.
    use.hammerdb(c)
    # create database for the given citus and pg versions
    if use_enterprise == 'on':
        use.postgres(c, pg_version)
        use.enterprise(c, citus_version)
        enterprise(c)
    else:
        use.postgres(c, pg_version)
        use.citus(c, citus_version)
        basic_testing(c)
    set_hammerdb_config(c, config_parser, driver_ip)

@task
def set_hammerdb_config(c, config_parser, driver_ip):
    total_mem_in_gb = total_memory_in_gb()
    mem_mib = total_mem_in_gb * 1024

    # these are the settings we use in hyperscale.
    shared_buffers_mib = int(0.25 * mem_mib)
    effective_cache_size_mib = int(mem_mib - shared_buffers_mib)
    maintenance_work_mem_mib = int(82.5 * math.log(total_mem_in_gb, 10) + 40)
    work_mem_mib = int(30 * math.log(total_mem_in_gb, 10) + 10)

    pg.set_config_str(c, "shared_buffers = '{}MB'".format(shared_buffers_mib))
    pg.set_config_str(c, "effective_cache_size = '{}MB'".format(effective_cache_size_mib))
    pg.set_config_str(c, "maintenance_work_mem = '{}MB'".format(maintenance_work_mem_mib))
    pg.set_config_str(c, "work_mem = '{}MB'".format(work_mem_mib))

    postgresql_conf_list = eval(config_parser.get('DEFAULT', 'postgresql_conf'))
    for postgresql_conf in postgresql_conf_list:
        pg.set_config_str(c, postgresql_conf)

    pg_latest = config.PG_LATEST
    with c.cd('{}/data'.format(pg_latest)):
        c.run('echo "host all all {}/16 trust" >> pg_hba.conf'.format(driver_ip))

    pg.restart(c)

def total_memory_in_gb():
    mem_bytes = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')  # e.g. 4015976448
    mem_gib = mem_bytes/(1024.**3)
    return mem_gib

def common_setup(c, build_citus_func, extension_install_tasks=[]):
    c.run('pkill -9 postgres || true', hide='stdout')

    prefix.check_for_pg_latest(c)
    # empty it but don't delete the link
    c.run('rm -rf {}/* || true'.format(config.PG_LATEST))

    redhat_install_packages(c)
    build_postgres(c)
    build_citus_func(c)
    build_extensions(c, extension_install_tasks)
    create_database(c)
    pg.start(c)

    pg_latest = config.PG_LATEST
    with c.cd(pg_latest):
        while getattr(c.run('bin/pg_isready'), 'return_code') != 0:
            print ('Waiting for database to be ready')

        c.run('bin/createdb $(whoami)')

    utils.psql(c, 'CREATE EXTENSION citus;', hide='stdout')

def add_workers(c):
    with c.cd('{}/data'.format(config.PG_LATEST)):
        workers = Connection.workers
        utils.psql(workers, 'SELECT master_add_node(\'{}\', 5432);'.format(ip))
        workers.run('echo "{} 5432" >> pg_worker_list.conf'.format(ip), hide='stdout')

def redhat_install_packages(c):
    # you can detect amazon linux with /etc/issue and redhat with /etc/redhat-release
    c.sudo("yum groupinstall -q -y 'Development Tools'", hide='stdout')

    c.sudo('yum install -q -y libxml2-devel libxslt-devel'
        ' openssl-devel pam-devel readline-devel libcurl-devel git libzstd-devel lz4-devel', hide='stdout')

def build_postgres(c):
    'Installs postges'

    # Give the postgres source to the remote nodes
    sourceball_loc = utils.download_pg()
    if c.host != 'localhost':
        c.put(local_path=sourceball_loc, remote_path=sourceball_loc)

    with c.cd(config.PG_SOURCE_BALLS):
        final_dir = os.path.basename(sourceball_loc).split('.tar.bz2')[0]
        # rm makes this idempotent, if not a bit inefficient

        utils.rmdir(c, final_dir)
        c.run('tar -xf {}.tar.bz2'.format(final_dir), hide='stdout')

        with c.cd(final_dir):
            pg_latest = config.PG_LATEST
            flags = ' '.join(config.PG_CONFIGURE_FLAGS)
            c.run('./configure --prefix={} {}'.format(pg_latest, flags), hide='stdout')

            core_count = c.run('cat /proc/cpuinfo | grep "core id" | wc -l')

            c.run('make -s -j{} install'.format(core_count), hide='stdout')

            with c.cd('contrib'):
                c.run('make -s install', hide='stdout')

def build_extensions(c, extension_install_tasks):
    for extension_install_task in extension_install_tasks:
        # we already execute on all workers, so do NOT use execute(extension_install_task)
        extension_install_task.run(c)

def build_citus(c):
    repo = config.CITUS_REPO
    utils.rmdir(c, repo, force=True) # force because git write-protects files

    c.run('git clone -q https://github.com/citusdata/citus.git {}'.format(repo))
    with c.cd(repo):
        git_ref = config.settings.get('citus-git-ref', 'master')
        c.run('git checkout {}'.format(git_ref))

        pg_latest = config.PG_LATEST
        run('PG_CONFIG={}/bin/pg_config ./configure'.format(pg_latest), hide='stdout')

        core_count = c.run('cat /proc/cpuinfo | grep "core id" | wc -l', hide='stdout')

        install_citus(c, core_count)

def build_enterprise(c):
    utils.add_github_to_known_hosts(c) # make sure ssh doesn't prompt
    repo = config.ENTERPRISE_REPO
    utils.rmdir(c, repo, force=True)
    if config.settings[config.IS_SSH_KEYS_USED]:
        c.run('git clone -q git@github.com:citusdata/citus-enterprise.git {}'.format(repo))
    else:
        c.run('git clone -q https://github.com/citusdata/citus-enterprise.git {}'.format(repo))
    with c.cd(repo):
        git_ref = config.settings.get('citus-git-ref', 'enterprise-master')
        c.run('git checkout {}'.format(git_ref))

        pg_latest = config.PG_LATEST
        run('PG_CONFIG={}/bin/pg_config ./configure'.format(pg_latest), hide='stdout')

        core_count = c.run('cat /proc/cpuinfo | grep "core id" | wc -l')

        install_citus(c, core_count)

def install_citus(c, core_count):
    # fall back to "make install" if "make install-all" is not available
    c.run('make -s -j{core_count} install-all || make -s -j{core_count} install'.\
        format(core_count=core_count), hide='stdout')

def create_database(c):
    pg_latest = config.PG_LATEST
    with c.cd(pg_latest):
        c.run('bin/initdb -D data', hide='stdout')
    with c.cd('{}/data'.format(pg_latest)):
        c.run('echo "shared_preload_libraries = \'citus\'" >> postgresql.conf')
        c.run('echo "max_prepared_transactions = 100" >> postgresql.conf')
        c.run('echo "listen_addresses = \'*\'" >> postgresql.conf')
        c.run('echo "wal_level = \'logical\'" >> postgresql.conf')
        c.run('echo "host all all 10.192.0.0/16 trust" >> pg_hba.conf')
