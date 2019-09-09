from fabric.api import task, run, cd, runs_once, roles, execute, settings

import config
import use
import prefix
import pg
import setup
import utils
import re
import add
import constants
import ConfigParser
import time

__all__ = ['jdbc', 'regression', 'pgbench_tests', 'update', 'tpch_automate']


@task
@runs_once
@roles('master')
def jdbc():
    'Assumes add.jdbc and add.tpch have been run'
    with cd('/home/ec2-user/test-automation/jdbc'):
        run('javac JDBCReleaseTest.java')
        run('java -classpath postgresql-9.4.1212.jre6.jar:. JDBCReleaseTest')


@task
@roles('master')
def regression():
    'Runs Citus\' regression tests'
    with cd(config.paths['citus-repo']):
        run('make check')


@task
@runs_once
@roles('master')
def pgbench_tests(config_file='pgbench_default.ini', connectionURI=''):
    config_parser = ConfigParser.ConfigParser()

    config_folder_path = "/home/ec2-user/test-automation/fabfile/pgbench_confs/"
    config_parser.read(config_folder_path + config_file)

    current_time_mark = time.strftime('%Y-%m-%d-%H-%M')
    results_file = open(config.paths['home-directory'] + 'pgbench_results_{}.csv'.format(current_time_mark), 'w')

    use_enterprise = config_parser.get('DEFAULT', 'use_enterprise')

    if connectionURI == '':
        results_file.write("Test, PG Version, Citus Version, Shard Count, Replication Factor, Latency Average, "
                           "TPS Including Connections, TPS Excluding Connections\n")

        pg_citus_tuples = eval(config_parser.get('DEFAULT', 'postgres_citus_versions'))
        for pg_version, citus_version in pg_citus_tuples:

            # create database for the given citus and pg versions
            if use_enterprise == 'on':
                citus_print_version = 'EE-' + citus_version
                execute(use.postgres, pg_version)
                execute(use.enterprise, citus_version)
                setup.enterprise()
            else:
                citus_print_version = 'CE-' + citus_version
                execute(use.postgres, pg_version)
                execute(use.citus, citus_version)
                setup.basic_testing()

            postgresql_conf_list = eval(config_parser.get('DEFAULT', 'postgresql_conf'))
            for postgresql_conf in postgresql_conf_list:
                execute(pg.set_config_str, postgresql_conf)

            execute(pg.restart)

            shard_count_replication_factor_tuples = eval(config_parser.get('DEFAULT', 'shard_counts_replication_factors'))
            for shard_count, replication_factor in shard_count_replication_factor_tuples:

                for section in config_parser.sections():
                    for option in config_parser.options(section):

                        if option == 'pgbench_command':
                            command = config_parser.get(section, 'pgbench_command')
                            out_val = run(command)

                            if section != 'initialization':

                                results_file.write(section + ", PG=" + pg_version + ", Citus=" + citus_print_version + ", " +
                                                   str(shard_count) + ", " + str(replication_factor))

                                if getattr(out_val, 'return_code') != 0:
                                    results_file.write('PGBENCH FAILED')

                                else:
                                    latency_average = re.search('latency average = (.+?) ms', out_val).group(1)
                                    tps_including_connections = \
                                        re.search('tps = (.+?) \(including connections establishing\)', out_val).group(1)
                                    tps_excluding_connections = \
                                        re.search('tps = (.+?) \(excluding connections establishing\)', out_val).group(1)

                                    results_file.write(", " + latency_average)
                                    results_file.write(", " + tps_including_connections)
                                    results_file.write(", " + tps_excluding_connections)
                                    results_file.write('\n')

                        elif option == 'distribute_table_command':
                            distribute_table_command = config_parser.get(section, 'distribute_table_command')
                            sql_command = ("SET citus.shard_count TO {}; "
                                           "SET citus.shard_replication_factor TO {}; ".format(shard_count,
                                                                                               replication_factor))

                            sql_command += distribute_table_command
                            utils.psql(sql_command)

                        elif option == 'sql_command':
                            sql_command = config_parser.get(section, 'sql_command')
                            utils.psql(sql_command)

            execute(pg.stop)

    else:
        results_file.write("Test, Connection String, Latency Average, "
                           "TPS Including Connections, TPS Excluding Connections\n")

        for section in config_parser.sections():
             for option in config_parser.options(section):

                if option == 'pgbench_command':
                    command = config_parser.get(section, 'pgbench_command')
                    command = command.replace("pgbench", "pgbench {}".format(connectionURI), 1)
                    out_val = run(command)

                    if section != 'initialization':

                        results_file.write(section + ", " + connectionURI)

                        if getattr(out_val, 'return_code') != 0:
                            results_file.write('PGBENCH FAILED')

                        else:
                            latency_average = re.search('latency average = (.+?) ms', out_val).group(1)
                            tps_including_connections = \
                                re.search('tps = (.+?) \(including connections establishing\)', out_val).group(1)
                            tps_excluding_connections = \
                                re.search('tps = (.+?) \(excluding connections establishing\)', out_val).group(1)

                            results_file.write(", " + latency_average)
                            results_file.write(", " + tps_including_connections)
                            results_file.write(", " + tps_excluding_connections)
                            results_file.write('\n')

                elif option == 'sql_command':
                    sql_command = config_parser.get(section, 'sql_command')
                    utils.psql(sql_command, connectionURI)

    results_file.close()

@task
@runs_once
@roles('master')
def tpch_automate(config_file='tpch_default.ini', connectionURI=''):
    config_parser = ConfigParser.ConfigParser()

    config_folder_path = "/home/ec2-user/test-automation/fabfile/tpch_confs/"
    config_parser.read(config_folder_path + config_file)

    for section in config_parser.sections():
        use_enterprise = config_parser.get(section, 'use_enterprise')
        pg_citus_tuples = eval(config_parser.get(section, 'postgres_citus_versions'))
        scale_factor = config_parser.get(section, 'scale_factor')

        for pg_version, citus_version in pg_citus_tuples:
            if use_enterprise == 'on':
                execute(use.postgres, pg_version)
                execute(use.enterprise, citus_version)
                setup.enterprise()
            else:
                execute(use.postgres, pg_version)
                execute(use.citus, citus_version)
                setup.basic_testing()

            execute(add.tpch, connectionURI= connectionURI, scale_factor=scale_factor)
            execute(tpch_queries, eval(config_parser.get(section, 'tpch_tasks_executor_types')), connectionURI,
                    pg_version, citus_version)
            execute(pg.stop)


@task
@roles('master')
def tpch_queries(query_info, connectionURI, pg_version, citus_version):
    results_file = open(
        config.paths['home-directory'] + 'tpch_benchmark_results_PG-{}_Citus-{}.txt'.format(pg_version, citus_version),
        'a')
    psql = '{}/bin/psql'.format(config.paths['pg-latest'])
    tpch_path = '{}/tpch_2_13_0/distributed_queries/'.format(config.paths['tests-repo'])

    for query_code, executor_type in query_info:
        executor_string = "set citus.task_executor_type to '{}'".format(executor_type)
        run_string = '{} {} -c "{}" -c "\\timing" -f "{}"'.format(psql, connectionURI, executor_string, tpch_path + query_code)
        out_val = run(run_string)
        results_file.write(out_val)
        results_file.write('\n')

@task
@runs_once
@roles('master')
def update():
     citus_versions = ['release-8.0', 'release-8.1']
     pg_version = '11.5'
     for citus_version in citus_versions:
        run_citus_update(citus_version, pg_version)
        run_citus_update_forces_restart(citus_version, pg_version)


def run_citus_update_forces_restart(citus_version, pg_version):
    results_file = open(
        config.paths['home-directory'] + 'update_forces_restart_PG-{}_Citus-{}.txt'.format(pg_version, citus_version),
        'a')
    execute(utils.psql, constants.DROP_CITUS)
    execute(setup.install_citus, citus_version)
    execute(utils.psql, constants.CREATE_CITUS)

    execute(use.citus, 'master')
    execute(setup.build_citus)
    with settings(warn_only=True):
        results_file.write(utils.psql(constants.ALTER_CITUS))


def run_citus_update(citus_version, pg_version):
    results_file = open(
        config.paths['home-directory'] + 'update_results_PG-{}_Citus-{}.txt'.format(pg_version, citus_version),
        'a')
    execute(utils.psql, constants.DROP_CITUS)
    execute(setup.install_citus, citus_version)
    execute(utils.psql, constants.CREATE_CITUS)
    execute(setup.add_workers)
    results_file.write(utils.psql('\dx'))

    execute(setup.install_citus, 'master')
    execute(utils.psql, constants.ALTER_CITUS)
    results_file.write(utils.psql('\dx'))
