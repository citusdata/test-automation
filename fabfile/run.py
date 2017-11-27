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

__all__ = ['jdbc', 'regression', 'dml_tests', 'tpch_automate']

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
def dml_tests(*args):
    'Runs pg-bench dml tests using the given config options'
    results_file = open(config.paths['home-directory'] + 'dml_benchmark_results.csv', 'w')
    config_parser = ConfigParser.ConfigParser()

    # If no argument is given, run default tests
    # Note that you can change test sql by updating insert.sql, update.sql and delete.sql
    if len(args) == 0:
        config_parser.read('fabfile/default_config.ini')
    elif len(args) == 1:
        config_parser.read(args)
    else:
        print('You should use the default config or give the name of your own config file')

    # before tests, create a file for the copy. We have to create this file since copy
    # benchmark get the data from this file.
    copy_file = open('copy_data_file', 'w')
    for i in range(1,10000):
        copy_file.write(str(i) + ',' + str(i) + ',' + str(i) + ',' + str(i))
        if i != 9999:
            copy_file.write('/n')

    for section in config_parser.sections():
        pg_citus_tuples = eval(config_parser.get(section, 'postgres_citus_versions'))
        for pg_version, citus_version in pg_citus_tuples:

            # create database for the given citus and pg versions
            prepare_for_benchmark(pg_version, citus_version)
            configure_and_run_postgres('10GB', '1h', 1000, 1000)

            shard_count_replication_factor_tuples = eval(config_parser.get(section, 'shard_counts_replication_factors'))
            for shard_count, replication_factor in shard_count_replication_factor_tuples:

                results_file.write(section + ", " + pg_version + ", " + citus_version + ", " +
                                   str(shard_count) + ", " + str(replication_factor) + ", ")
                print_to_std = section + ", " + pg_version + ", " + citus_version + ", " + \
                                str(shard_count) + ", " + str(replication_factor) + ", "

                psql_command = ("SET citus.multi_shard_commit_protocol TO '1pc'; "
                                "SET citus.shard_count TO {}; " 
                                "SET citus.shard_replication_factor TO {}; "
                                "CREATE TABLE test_table(a int, b int, c int, d int); ").format(shard_count, replication_factor)

                if config_parser.get(section, 'use_reference_table') == 'no':
                    psql_command += "SELECT create_distributed_table('test_table', 'a');"
                else:
                    psql_command += ("SELECT create_reference_table('test_table'); "
                                     "SET citus.multi_shard_commit_protocol TO '2pc';")

                utils.psql(psql_command)

                command = 'pgbench -c {} -j {} -f {} -n -t {} -P 5'.format(config_parser.get(section, 'client_count'),
                                                                           config_parser.get(section, 'thread_count'),
                                                                           config_parser.get(section, 'filename'),
                                                                           config_parser.get(section, 'transaction_count'))

                out_val = run(command)
                if getattr(out_val, 'return_code') != 0:
                    results_file.write('PG_BENCH FAILED')
                    print_to_std += 'PG_BENCH_FAILED'

                else:
                    results_file.write(re.search('tps = (.+?) ', out_val).group(1))
                    results_file.write('\n')
                    print_to_std += re.search('tps = (.+?) ', out_val).group(1)
                    print_to_std += '\n'

                print (print_to_std)
                utils.psql("DROP TABLE test_table;")

            execute(pg.stop)

    results_file.close()


def prepare_for_benchmark(pg_version, citus_version):
    execute(prefix.set_prefix, config.paths['home-directory'] + 'pg-' + pg_version + '-citus-' + citus_version)
    execute(use.postgres, pg_version)
    execute(use.citus, citus_version)
    execute(setup.basic_testing)
    

def configure_and_run_postgres(max_val_size, checkpoint_timeout, max_connections, max_prepared_transactions):
    execute(pg.set_config, 'max_wal_size', "'{}'".format(max_val_size))
    execute(pg.set_config, 'checkpoint_timeout', "'{}'".format(checkpoint_timeout))
    execute(pg.set_config, 'max_connections', max_connections)
    execute(pg.set_config, 'max_prepared_transactions', max_prepared_transactions)
    execute(pg.stop)
    execute(pg.start)


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
            execute(tpch_queries, eval(config_parser.get(section, 'tpch_tasks_executor_types')))
            execute(pg.stop)


@task
@roles('master')
def tpch_queries(query_info):
    results_file = open(config.paths['home-directory'] + 'tpch_benchmark_results.csv', 'a')
    psql = '{}/bin/psql'.format(config.paths['pg-latest'])
    tpch_path = '{}/tpch_2_13_0/queries/'.format(config.paths['tests-repo'])

    for query_code, executor_type in query_info:
        executor_string = "set citus.task_executor_type to '{}'".format(executor_type)
        run_string = '{} -1 -c "{}" -c "\\timing" -f "{}"'.format(psql, executor_string, tpch_path + query_code)
        out_val = run(run_string)
        results_file.write(out_val)
        results_file.write('\n')
