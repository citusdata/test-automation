'''
Tasks which are aimed at facilitating specific components of our release testing.

Ideally you can run `fab setup.tpch`, for example, and immdiately start running tpc-h
queries.
'''
from doctest import master
import os.path
import os
import math

from invoke import task

import cache
import utils
import multi_connections
import config
import configparser
import pg
import add
import use
import prefix
import use
from connection import master_connection, all_connections, worker_hosts

@task
def basic_testing(c):
    'Sets up a no-frills Postgres+Citus cluster'
    if not multi_connections.is_coordinator_connection(c):
        return

    if multi_connections.execute_on_all_nodes_if_no_hosts(c, basic_testing):
        return

    multi_connections.execute(all_connections, prefix.ensure_pg_latest_exists, default=config.POSTGRES_INSTALLATION)
    multi_connections.execute(all_connections, common_setup, build_citus)
    add_workers(master_connection)

@task
def extension_testing(c, ext_to_test, extension_install_tasks, extension_configure_task):
    'Sets up Postgres + Citus cluster with the extensions in given order'
    if not multi_connections.is_coordinator_connection(c):
        return

    if multi_connections.execute_on_all_nodes_if_no_hosts(c, extension_testing):
        return

    # extension testing supports runs only for single node setup
    multi_connections.execute(all_connections, prefix.ensure_pg_latest_exists, default=config.POSTGRES_INSTALLATION)
    multi_connections.execute(all_connections, extension_setup, ext_to_test, extension_install_tasks, extension_configure_task)

@task
def tpch(c):
    'Just like basic_testing, but also includes some files useful for tpc-h'
    if not multi_connections.is_coordinator_connection(c):
        return

    if multi_connections.execute_on_all_nodes_if_no_hosts(c, tpch):
        return

    multi_connections.execute(all_connections, prefix.ensure_pg_latest_exists, default=config.POSTGRES_INSTALLATION)
    multi_connections.execute(all_connections, common_setup, build_citus)
    add_workers(master_connection)
    multi_connections.execute(all_connections, add.tpch)

@task
def valgrind(c):
    # prepare yum install command
    if multi_connections.execute_on_all_nodes_if_no_hosts(c, valgrind):
        return

    install_required_packages_command = 'yum install -q -y ' + ' '.join(config.VALGRIND_REQUIRED_PACKAGES)

    # install libraries required for valgrind test
    c.sudo(install_required_packages_command)

    # create results directory to put resulting log files there
    # (for pushing them to results repository)
    utils.rmdir(c, config.RESULTS_DIRECTORY, force=True)
    utils.mkdir_if_not_exists(config.RESULTS_DIRECTORY)

    # set build citus function
    build_citus_func = config.settings[config.BUILD_CITUS_FUNC]
    multi_connections.execute(all_connections, prefix.ensure_pg_latest_exists, default=config.POSTGRES_INSTALLATION)
    multi_connections.execute(all_connections, common_setup, build_citus_func)

@task(optional=['config-file', 'driver-ip'])
def hammerdb(c, config_file='hammerdb.ini', driver_ip=''):
    if not multi_connections.is_coordinator_connection(c):
        return

    if multi_connections.execute_on_all_nodes_if_no_hosts(c, hammerdb, config_file=config_file, driver_ip=driver_ip):
        return

    config_parser = configparser.ConfigParser()

    config_path = os.path.join(config.HOME_DIR, "test-automation/fabfile/hammerdb_confs", config_file)
    config_parser.read(config_path)

    pg_version, citus_version = eval(config_parser.get('DEFAULT', 'postgres_citus_version'))
    # this should be run before any setup so that it sets the necessary fields.
    multi_connections.execute(all_connections, use.hammerdb)
    # create database for the given citus and pg versions
    multi_connections.execute(all_connections, use.postgres, pg_version)
    multi_connections.execute(all_connections, use.citus, citus_version)
    basic_testing(c)
    multi_connections.execute(all_connections, set_hammerdb_config, config_parser, driver_ip)

@task
def set_hammerdb_config(c, config_parser, driver_ip):
    if multi_connections.execute_on_all_nodes_if_no_hosts(c, set_hammerdb_config, config_parser, driver_ip):
        return

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

def common_setup(c, build_citus_func):
    # make it ready to install a new postgres version
    kill_postgres(c)
    clean_postgres_data_dir(c)

    # build and install postgres and citus versions
    redhat_install_packages(c)
    build_postgres(c)
    build_citus_func(c)

    # create db directory and configure it
    pg.create(c)
    configure_database(c)

    # start db and create default db + citus extension
    pg.start(c)
    create_db(c)
    create_citus(c)

def extension_setup(c, ext_to_test, extension_install_tasks, extension_configure_task):
    # make it ready to install a new postgres version
    kill_postgres(c)
    clean_postgres_data_dir(c)

    # build and install postgres and required extensions for the test
    redhat_install_packages(c)
    build_postgres(c)
    build_extensions(c, extension_install_tasks)

    # create db directory and configure it
    pg.create(c)
    configure_database(c)
    configure_extensions(c, extension_configure_task)

    # start db and create default db and extensions after db starts
    pg.start(c)
    create_db(c)
    create_extensions(c, ext_to_test, extension_install_tasks)

def kill_postgres(c):
    c.run('pkill -9 postgres || true', hide='stdout')

def clean_postgres_data_dir(c):
    prefix.check_for_pg_latest(c)
    # delete data dir
    c.run('rm -rf {}/data || true'.format(config.PG_LATEST))

def create_db(c):
    pg_latest = config.PG_LATEST
    with c.cd(pg_latest):
        while c.run('bin/pg_isready').exited != 0:
            print ('Waiting for database to be ready')

        c.run('bin/createdb $(whoami)')

def create_citus(c):
    utils.psql(c, 'CREATE EXTENSION citus;')

def create_extensions(c, ext_to_test, extension_install_tasks):
    for extension_install_task in extension_install_tasks:
        if extension_install_task.name != ext_to_test: # ext_to_test will be created by extension's test file
            extension_install_task.create_extension(c)

def add_workers(c):
    if not multi_connections.is_coordinator_connection(c):
        return

    with c.cd('{}/data'.format(config.PG_LATEST)):
        for worker_host in worker_hosts:
            utils.psql(c, 'SELECT master_add_node(\'{}\', 5432);'.format(worker_host))
            c.run('echo "{} 5432" >> pg_worker_list.conf'.format(worker_host), hide='stdout')

def redhat_install_packages(c):
    # you can detect amazon linux with /etc/issue and redhat with /etc/redhat-release
    c.sudo("yum groupinstall -q -y 'Development Tools'", hide='stdout')

    c.sudo('yum install -q -y libxml2-devel libxslt-devel'
        ' openssl-devel pam-devel readline-devel libcurl-devel'
        ' git libzstd-devel lz4-devel perl-IPC-Run perl-Test-Simple'
        ' perl-Test-Harness perl-Time-HiRes', hide='stdout')

# cache to not build and install the same version of postgres or extensions
# we will only reinstall pg if its version changes.
# we will only reinstall an extension if its git_ref or pg-version changes
_build_cache = cache.Cache()

def _pg_package_name(c):
    connection_name = multi_connections.name_of_connection(c)
    version = config.PG_VERSION
    pg_name = 'con-{}-pg-{}'.format(connection_name, version)
    return pg_name

def build_postgres(c):
    'Installs postgres'

    package_name = _pg_package_name(c)
    if _build_cache.search_build_cache(package_name): # already installed current version
        return
    _build_cache.insert_build_cache(package_name)

    # download postgres source
    sourceball_loc = utils.download_pg(c)

    with c.cd(config.PG_SOURCE_BALLS):
        final_dir = os.path.basename(sourceball_loc).split('.tar.bz2')[0]
        # rm makes this idempotent, if not a bit inefficient

        utils.rmdir(c, final_dir)
        c.run('tar -xf {}.tar.bz2'.format(final_dir), hide='stdout')

        with c.cd(final_dir):
            pg_latest = config.PG_LATEST
            flags = ' '.join(config.PG_CONFIGURE_FLAGS)
            c.run('./configure --prefix={} {}'.format(pg_latest, flags), hide='stdout')

            core_count = utils.get_core_count()
            c.run('make -s -j{} install'.format(core_count), hide='stdout')

            with c.cd('contrib'):
                c.run('make -s -j{} install'.format(core_count), hide='stdout')

def build_extensions(c, extension_install_tasks):
    for extension_install_task in extension_install_tasks:
        package_name = extension_install_task.get_unique_package_name(c)
        if not _build_cache.search_build_cache(package_name):
            extension_install_task.run(c)
            _build_cache.insert_build_cache(package_name)

def build_citus(c):
    repo = config.CITUS_REPO
    utils.rmdir(c, repo, force=True) # force because git write-protects files
    c.run('git clone -q https://github.com/citusdata/citus.git {}'.format(repo))
    with c.cd(repo):
        git_ref = config.settings.get('citus-git-ref', 'master')
        c.run('git checkout {}'.format(git_ref))

        pg_latest = config.PG_LATEST
        c.run('PG_CONFIG={}/bin/pg_config ./configure'.format(pg_latest), hide='stdout')

        core_count = utils.get_core_count()
        install_citus(c, core_count)

def install_citus(c, core_count):
    # fall back to "make install" if "make install-all" is not available
    c.run('make -s -j{core_count} install-all || make -s -j{core_count} install'.\
        format(core_count=core_count), hide='stdout')

def configure_database(c):
    pg_latest = config.PG_LATEST
    with c.cd('{}/data'.format(pg_latest)):
        c.run('echo "shared_preload_libraries = \'citus\'" >> postgresql.conf')
        c.run('echo "max_prepared_transactions = 100" >> postgresql.conf')
        c.run('echo "listen_addresses = \'*\'" >> postgresql.conf')
        c.run('echo "wal_level = \'logical\'" >> postgresql.conf')
        c.run('echo "host all all 10.192.0.0/16 trust" >> pg_hba.conf')

def configure_extensions(c, extension_configure_task):
    if extension_configure_task:
        extension_configure_task.configure(c)
