from invoke import task
from invoke.exceptions import Exit

import config
import use
import pg
import setup
import add
from add import Extension, ExtensionTest
import utils
import multi_connections
from connection import all_connections

import re
import os
import configparser
import time

@task
def jdbc(c):
    'Assumes add.jdbc and add.tpch have been run'
    if not multi_connections.is_coordinator_connection(c):
        return

    if multi_connections.execute_on_all_nodes_if_no_hosts(c, jdbc):
        return

    with c.cd(config.HOME_DIR + '/test-automation/jdbc'):
        c.run('javac JDBCReleaseTest.java')
        c.run('java -classpath postgresql-9.4.1212.jre6.jar:. JDBCReleaseTest')


@task
def regression(c):
    'Runs Citus\' regression tests'
    if not multi_connections.is_coordinator_connection(c):
        return

    if multi_connections.execute_on_all_nodes_if_no_hosts(c, regression):
        return

    with c.cd(config.CITUS_REPO):
        c.run('make check')


@task(optional=['config-file', 'connectionURI'])
def pgbench_tests(c, config_file='pgbench_default.ini', connectionURI=''):
    if not multi_connections.is_coordinator_connection(c):
        return

    if multi_connections.execute_on_all_nodes_if_no_hosts(c, pgbench_tests, config_file=config_file, connectionURI=connectionURI):
        return

    config_parser = configparser.ConfigParser()

    config_folder_path = os.path.join(config.HOME_DIR, config.TEST_REPO, "fabfile/pgbench_confs/")
    config_parser.read(config_folder_path + config_file)


    current_time_mark = time.strftime('%Y-%m-%d-%H-%M')
    utils.mkdir_if_not_exists(config.RESULTS_DIRECTORY)
    path = os.path.join(config.RESULTS_DIRECTORY, 'pgbench_results_{}_{}.csv'.format(current_time_mark, config_file))
    results_file = open(path, 'w')

    if connectionURI == '':
        results_file.write("Test, PG Version, Citus Version, Shard Count, Replication Factor, Latency Average, "
                           "TPS Excluding Connections, TPS Including Connections\n")

        pg_citus_tuples = eval(config_parser.get('DEFAULT', 'postgres_citus_versions'))
        for pg_version, citus_version in pg_citus_tuples:

            # create database for the given citus and pg versions
            citus_print_version = 'CE-' + citus_version
            multi_connections.execute(all_connections, use.postgres, pg_version)
            multi_connections.execute(all_connections, use.citus, citus_version)
            setup.basic_testing(c)

            postgresql_conf_list = eval(config_parser.get('DEFAULT', 'postgresql_conf'))
            for postgresql_conf in postgresql_conf_list:
                multi_connections.execute(all_connections, pg.set_config_str, postgresql_conf)

            multi_connections.execute(all_connections, pg.restart)

            shard_count_replication_factor_tuples = eval(config_parser.get('DEFAULT', 'shard_counts_replication_factors'))
            for shard_count, replication_factor in shard_count_replication_factor_tuples:
                for section in config_parser.sections():
                    for option in config_parser.options(section):

                        if option == 'pgbench_command':
                            command = config_parser.get(section, 'pgbench_command')
                            command_result = c.run(command)
                            out_val = command_result.stdout.strip()

                            if section != 'initialization':

                                results_file.write(section + ", PG=" + pg_version + ", Citus=" + citus_print_version + ", " +
                                                   str(shard_count) + ", " + str(replication_factor))

                                if command_result.exited != 0:
                                    results_file.write('PGBENCH FAILED')

                                else:
                                    latency_average = re.search('latency average = (.+?) ms', out_val).group(1)
                                    results_file.write(", " + latency_average)

                                    if re.search('tps = (.+?) \(including connections establishing\)', out_val) != None:
                                        # With PG14, the output is slightly different so we handle that.
                                        tps_including_connections = \
                                            re.search('tps = (.+?) \(including connections establishing\)', out_val).group(1)
                                        tps_excluding_connections = \
                                            re.search('tps = (.+?) \(excluding connections establishing\)', out_val).group(1)
                                        results_file.write(", " + tps_excluding_connections)
                                        results_file.write(", " + tps_including_connections)

                                    else:
                                        tps_excluding_connections = \
                                            re.search('tps = (.+?) \(without initial connection time\)', out_val).group(1)
                                        results_file.write(", " + tps_excluding_connections)
                                        results_file.write(", N\A")


                                    results_file.write('\n')

                        elif option == 'distribute_table_command':
                            distribute_table_command = config_parser.get(section, 'distribute_table_command')
                            sql_command = ("SET citus.shard_count TO {}; "
                                           "SET citus.shard_replication_factor TO {}; ".format(shard_count,
                                                                                               replication_factor))

                            sql_command += distribute_table_command
                            utils.psql(c, sql_command)

                        elif option == 'sql_command':
                            sql_command = config_parser.get(section, 'sql_command')
                            utils.psql(c, sql_command)

            multi_connections.execute(all_connections, pg.stop)
    else:
        results_file.write("Test, Connection String, Latency Average, "
                           "TPS Including Connections, TPS Excluding Connections\n")

        for section in config_parser.sections():
             for option in config_parser.options(section):

                if option == 'pgbench_command':
                    command = config_parser.get(section, 'pgbench_command')
                    command = command.replace("pgbench", "pgbench {}".format(connectionURI), 1)
                    command_result = c.run(command)
                    out_val = command_result.stdout.strip()

                    if section != 'initialization':

                        results_file.write(section + ", " + connectionURI)

                        if command_result.exited != 0:
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
                    utils.psql(c, sql_command, connectionURI)

    results_file.close()

@task(optional=['config-file', 'connectionURI'])
def tpch_automate(c, config_file='tpch_default.ini', connectionURI=''):
    if not multi_connections.is_coordinator_connection(c):
        return

    if multi_connections.execute_on_all_nodes_if_no_hosts(c, tpch_automate, config_file=config_file, connectionURI=connectionURI):
        return

    config_parser = configparser.ConfigParser()

    config_folder_path = os.path.join(config.HOME_DIR, config.TEST_REPO, "fabfile/tpch_confs/")
    config_parser.read(config_folder_path + config_file)

    for section in config_parser.sections():
        pg_citus_tuples = eval(config_parser.get(section, 'postgres_citus_versions'))
        scale_factor = config_parser.get(section, 'scale_factor')

        for pg_version, citus_version in pg_citus_tuples:
            multi_connections.execute(all_connections, use.postgres, pg_version)
            multi_connections.execute(all_connections, use.citus, citus_version)
            setup.basic_testing(c)

            multi_connections.execute(all_connections, add.tpch, connectionURI=connectionURI, scale_factor=scale_factor)
            multi_connections.execute(all_connections, tpch_queries, eval(config_parser.get(section, 'tpch_tasks_executor_types')), connectionURI,
                    pg_version, citus_version, config_file)
            multi_connections.execute(all_connections, pg.stop)

@task(optional=['config-file', 'connectionURI'])
def extension_tests(c, config_file='extension_default.ini', connectionURI=''):
    if not multi_connections.is_coordinator_connection(c):
        return

    if multi_connections.execute_on_all_nodes_if_no_hosts(c, extension_tests, config_file=config_file, connectionURI=connectionURI):
        return

    config_parser = configparser.ConfigParser()

    config_folder_path = os.path.join(config.HOME_DIR, config.TEST_REPO, "fabfile/extension_confs/")
    config_parser.read(config_folder_path + config_file)

    sections = config_parser.sections()
    for section in sections:
        if section == 'main':
            pg_versions = eval(config_parser.get(section, 'postgres_versions'))
            extension_regress_tests = get_extension_tests_from_config(config_parser)

            for pg_version in pg_versions:
                multi_connections.execute(all_connections, use.postgres, pg_version)

                # run each extension test scenario
                for extension_regress_test in extension_regress_tests:
                    # we need to restart pg because we modify preload_shared_libraries
                    ext_to_test = extension_regress_test.extension.name
                    extension_install_tasks = extension_regress_test.get_install_tasks()
                    configure_task = extension_regress_test.get_configure_task()

                    setup.extension_testing(c, ext_to_test, extension_install_tasks, configure_task)
                    extension_regress_test.regress(c)
                    multi_connections.execute(all_connections, pg.stop)

def get_extension_tests_from_config(config_parser):
    extension_tests= []
    test_count = eval(config_parser.get('main', 'test_count'))
    for i in range(1, test_count+1):
        test_name = 'test-{}'.format(i)
        extension_name = config_parser.get(test_name, 'ext_to_test')

        extension = Extension(extension_name)
        extension.parse_from_config(config_parser)

        extension_test = ExtensionTest(test_name, extension)
        extension_test.parse_from_config(config_parser)

        extension_tests.append(extension_test)

    return extension_tests

@task
def tpch_queries(c, query_info, connectionURI, pg_version, citus_version, config_file):
    if not multi_connections.is_coordinator_connection(c):
        return

    if multi_connections.execute_on_all_nodes_if_no_hosts(c, tpch_queries, query_info, connectionURI, pg_version, citus_version, config_file):
        return

    utils.mkdir_if_not_exists(config.RESULTS_DIRECTORY)
    path = os.path.join(config.RESULTS_DIRECTORY, 'tpch_benchmark_results_{}_PG-{}_Citus-{}.txt'.format(config_file, pg_version, citus_version))
    results_file = open(path, 'a')

    psql = '{}/bin/psql'.format(config.PG_LATEST)
    tpch_path = '{}/tpch_2_13_0/distributed_queries/'.format(config.TEST_REPO)

    for query_code, executor_type in query_info:
        executor_string = "set citus.task_executor_type to '{}'".format(executor_type)
        enable_repartition_joins = "set citus.enable_repartition_joins to 'on'"
        run_string = '{} {} -c "{}" -c "{}" -c "\\timing" -f "{}"'.format(psql, connectionURI,
            enable_repartition_joins, executor_string, tpch_path + query_code)
        out_val = c.run(run_string).stdout.strip()
        results_file.write(out_val)
        results_file.write('\n')

# If no citus valgrind logs exist results directory, then simply put valgrind_success
# file under results directory.
def valgrind_filter_put_results(c):
    'Filter valgrind test outputs, put success file if no citus related valgrind output'

    repo_path = config.settings[config.REPO_PATH]

    regression_test_path = os.path.join(repo_path, config.RELATIVE_REGRESS_PATH)

    regression_diffs_path = os.path.join(regression_test_path, config.REGRESSION_DIFFS_FILE)
    valgrind_logs_path = os.path.join(regression_test_path, config.VALGRIND_LOGS_FILE)

    citus_valgrind_logs_path = os.path.join(config.RESULTS_DIRECTORY, config.CITUS_RELATED_VALGRIND_LOG_FILE)
    success_file_path = os.path.join(config.RESULTS_DIRECTORY, config.VALGRIND_SUCCESS_FNAME)

    trace_ids_tmp_file = ".trace_ids"
    trace_ids_path = os.path.join(regression_test_path, trace_ids_tmp_file)

    # ship regression.diffs (if exists) to result folder
    if os.path.isfile(regression_diffs_path):
        c.run('mv {} {}'.format(regression_diffs_path, config.RESULTS_DIRECTORY))

    # filter the (possibly) citus-related outputs and put to results file if existz

    if os.path.isfile(valgrind_logs_path):

        # get stack trace id that includes calls to citus
        c.run('cat {} | grep -i "citus" | awk \'{{ print $1 }}\' | uniq  > {}'.format(valgrind_logs_path, trace_ids_path))

        if os.path.isfile(trace_ids_path) and os.path.getsize(trace_ids_path) > 0:
            # filter stack traces with stack trace ids that we found above (if any)
            c.run('while read line; do grep {} -e $line ; done < {} > {}'.format(
                valgrind_logs_path,
                trace_ids_path,
                citus_valgrind_logs_path))

        # cleanup
        c.run('rm {}'.format(trace_ids_path))

    # if we have no citus-related valgrind outputs then just put an empty file named as `config.VALGRIND_SUCCESS_FNAME`
    if not os.path.exists(citus_valgrind_logs_path):
        c.run('touch {}'.format(success_file_path))

def valgrind_internal(c, valgrind_target, schedule):
    'Runs valgrind tests'

    # set citus path variable
    repo_path = config.settings[config.REPO_PATH]

    use.valgrind(c)
    setup.valgrind(c)

    with c.cd(os.path.join(repo_path, config.RELATIVE_REGRESS_PATH)):

        # make check-multi-vg returns 2 in case of failures in regression tests
        # we should do failure handling here
        valgrind_logs_path=os.path.join(config.RESULTS_DIRECTORY, config.VALGRIND_LOGS_FILE)
        valgrind_test_out_path = os.path.join(config.RESULTS_DIRECTORY, config.VALGRIND_TEST_OUT_FILE)

        # wrap the command with tee to log stdout & stderr to a file in results directory as well
        # this is done to ensure that valgrind test is actually finished
        valgrind_test_command = 'CITUS_VALGRIND_LOG_FILE={} SCHEDULE={} make {}'.format(valgrind_logs_path, schedule, valgrind_target)
        valgrind_test_command = valgrind_test_command + ' 2>&1 | tee {}'.format(valgrind_test_out_path)

        c.run(valgrind_test_command, warn=True)

        valgrind_filter_put_results(c)

@task(positional=['target', 'schedule'])
def valgrind(c, target, schedule):
    'Choose a valgrind target. For example: fab ... run.valgrind check-multi-1-vg ...'
    if not multi_connections.is_coordinator_connection(c):
        return

    if multi_connections.execute_on_all_nodes_if_no_hosts(c, valgrind, target):
        return

    available_valgrind_targets = ('check-custom-schedule-vg', 'check-isolation-custom-schedule-vg', 'check-failure-custom-schedule-vg')
    if target not in available_valgrind_targets:
        raise Exit('Available targets for run.valgrind: {}'.
              format(', '.join(available_valgrind_targets)))

    valgrind_target = target
    valgrind_internal(c, valgrind_target, schedule)
