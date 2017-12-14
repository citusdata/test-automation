from fabric.api import task, run, cd, runs_once, roles, execute

import config
import use
import prefix
import pg
import setup
import utils
import re
import add
import ConfigParser
import time

__all__ = ['jdbc', 'regression', 'pgbench_tests', 'tpch_automate']


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
def pgbench_tests(*args):
    config_parser = ConfigParser.ConfigParser()

    # If no argument is given, run default tests

    config_folder_path = "/home/ec2-user/test-automation/pgbench_confs/"
    if len(args) == 0:
        config_parser.read(config_folder_path + "pgbench_default.ini")
    elif len(args) == 1:
        config_parser.read(config_folder_path + args[0])
    else:
        print('You should use the default config or give the name of your own config file')

    current_time_mark = time.strftime('%Y-%m-%d-%H-%M')
    results_file = open(config.paths['home-directory'] + 'pgbench_results_{}.csv'.format(current_time_mark), 'w')

    results_file.write("Test, PG Version, Citus Version, Shard Count, Replication Factor, Latency Average, "
                       "TPS Including Connections, TPS Excluding Connections\n")

    pg_citus_tuples = eval(config_parser.get('DEFAULT', 'postgres_citus_versions'))
    for pg_version, citus_version in pg_citus_tuples:

        # create database for the given citus and pg versions
        prepare_for_benchmark(pg_version, citus_version)

        postgresql_conf_list = eval(config_parser.get('DEFAULT', 'postgresql_conf'))
        for postgresql_conf in postgresql_conf_list:
            execute(pg.set_config, postgresql_conf)

        execute(pg.restart)

        shard_count_replication_factor_tuples = eval(config_parser.get('DEFAULT', 'shard_counts_replication_factors'))
        for shard_count, replication_factor in shard_count_replication_factor_tuples:

            for section in config_parser.sections():
                for option in config_parser.options(section):

                    if option == 'pgbench_command':
                        command = config_parser.get(section, 'pgbench_command')
                        out_val = run(command)

                        if section != 'initialization':

                            results_file.write(section + ", PG=" + pg_version + ", Citus=" + citus_version + ", " +
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

    results_file.close()


def prepare_for_benchmark(pg_version, citus_version):
    execute(prefix.set_prefix, config.paths['home-directory'] + 'pg-' + pg_version + '-citus-' + citus_version)
    execute(use.postgres, pg_version)
    execute(use.citus, citus_version)
    setup.basic_testing()


@task
@runs_once
@roles('master')
def tpch_automate(*args):
    'Runs tpch tests automatically given configuration file'

    config_parser = ConfigParser.ConfigParser()

    # If no argument is given, run default tests
    # Note that you can change test sql by updating insert.sql, update.sql and delete.sql
    if len(args) == 0:
        config_parser.read('fabfile/default_tpch_config.ini')
    elif len(args) == 1:
        config_parser.read(args)
    else:
        print('You should use the default config or give the name of your own config file')

    for section in config_parser.sections():
        pg_citus_tuples = eval(config_parser.get(section, 'postgres_citus_versions'))
        for pg_version, citus_version in pg_citus_tuples:
            prepare_for_benchmark(pg_version, citus_version)
            execute(add.tpch)
            execute(tpch_queries, eval(config_parser.get(section, 'tpch_tasks_executor_types')), pg_version,
                    citus_version)
            execute(pg.stop)


@task
@roles('master')
def tpch_queries(query_info, pg_version, citus_version):
    results_file = open(
        config.paths['home-directory'] + 'tpch_benchmark_results_PG-{}_Citus-{}.txt'.format(pg_version, citus_version),
        'a')
    psql = '{}/bin/psql'.format(config.paths['pg-latest'])
    tpch_path = '{}/tpch_2_13_0/distributed_queries/'.format(config.paths['tests-repo'])

    for query_code, executor_type in query_info:
        executor_string = "set citus.task_executor_type to '{}'".format(executor_type)
        run_string = '{} -1 -c "{}" -c "\\timing" -f "{}"'.format(psql, executor_string, tpch_path + query_code)
        out_val = run(run_string)
        results_file.write(out_val)
        results_file.write('\n')
