from fabric.api import task, run, cd, runs_once, roles, execute, abort
from fabric.context_managers import settings

import config
import use
import prefix
import pg
import setup
import utils
import re
import os
import add
from add import InstallExtensionTask
from add import RegressExtensionTask
import ConfigParser
import time

__all__ = ['jdbc', 'regression', 'pgbench_tests', 'tpch_automate', 'extension_tests', 'valgrind', 'valgrind_filter_put_results']


@task
@runs_once
@roles('master')
def jdbc():
    'Assumes add.jdbc and add.tpch have been run'
    with cd(config.HOME_DIR + '/test-automation/jdbc'):
        run('javac JDBCReleaseTest.java')
        run('java -classpath postgresql-9.4.1212.jre6.jar:. JDBCReleaseTest')


@task
@roles('master')
def regression():
    'Runs Citus\' regression tests'
    with cd(config.CITUS_REPO):
        run('make check')


@task
@runs_once
@roles('master')
def pgbench_tests(config_file='pgbench_default.ini', connectionURI=''):
    config_parser = ConfigParser.ConfigParser()

    config_folder_path = os.path.join(config.HOME_DIR, "test-automation/fabfile/pgbench_confs/")
    config_parser.read(config_folder_path + config_file)


    current_time_mark = time.strftime('%Y-%m-%d-%H-%M')
    utils.mkdir_if_not_exists(config.RESULTS_DIRECTORY)
    path = os.path.join(config.RESULTS_DIRECTORY, 'pgbench_results_{}_{}.csv'.format(current_time_mark, config_file))
    results_file = open(path, 'w')

    if connectionURI == '':
        use_enterprise = config_parser.get('DEFAULT', 'use_enterprise')

        results_file.write("Test, PG Version, Citus Version, Shard Count, Replication Factor, Latency Average, "
                           "TPS Excluding Connections, TPS Including Connections\n")

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

    config_folder_path = os.path.join(config.HOME_DIR, "test-automation/fabfile/tpch_confs/")
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
                    pg_version, citus_version, config_file)
            execute(pg.stop)


@task
@runs_once
@roles('master')
def extension_tests(config_file='extension_default.ini', connectionURI=''):
    config_parser = ConfigParser.ConfigParser()

    config_folder_path = os.path.join(config.HOME_DIR, "test-automation/fabfile/extension_confs/")
    config_parser.read(config_folder_path + config_file)

    sections = config_parser.sections()
    for section in sections:
        if section == 'main':
            pg_citus_tuples = eval(config_parser.get(section, 'postgres_citus_versions'))
            extensions = eval(config_parser.get(section, 'extensions'))
            extension_install_tasks = get_extension_install_tasks_from_config(extensions, config_parser)
            extension_regression_tasks = get_extension_regression_tasks_from_config(extensions, config_parser)

            for pg_version, citus_version in pg_citus_tuples:
                execute(use.postgres, pg_version)
                execute(use.citus, citus_version)
                setup.basic_testing(extension_install_tasks)

                # run extension tests for each extension
                for extension_regression_task in extension_regression_tasks:
                    # we only want to execute on coordinator, so do NOT use execute(extension_install_task)
                    extension_regression_task.run()

                execute(pg.stop)

def get_extension_install_tasks_from_config(extensions, config_parser):
    extension_install_tasks = []
    for extension in extensions:
        doc = config_parser.get(extension, 'doc')
        repo_url = config_parser.get(extension, 'repo_url')
        default_git_ref = config_parser.get(extension, 'default_git_ref')

        extension_install_task = InstallExtensionTask(
            task_name=extension,
            doc=doc,
            repo_url=repo_url,
            default_git_ref=default_git_ref,
        )
        extension_install_tasks.append(extension_install_task)

    return extension_install_tasks

def get_extension_regression_tasks_from_config(extensions, config_parser):
    extension_regression_tasks = []
    for extension in extensions:
        doc = config_parser.get(extension, 'doc')
        repo_url = config_parser.get(extension, 'repo_url')
        default_git_ref = config_parser.get(extension, 'default_git_ref')

        extension_regression_task = RegressExtensionTask(
            task_name=extension,
            doc=doc,
            repo_url=repo_url,
            default_git_ref=default_git_ref,
        )
        extension_regression_tasks.append(extension_regression_task)

    return extension_regression_tasks

@task
@roles('master')
def tpch_queries(query_info, connectionURI, pg_version, citus_version, config_file):
    utils.mkdir_if_not_exists(config.RESULTS_DIRECTORY)
    path = os.path.join(config.RESULTS_DIRECTORY, 'tpch_benchmark_results_{}_PG-{}_Citus-{}.txt'.format(config_file, pg_version, citus_version))
    results_file = open(path, 'a')

    psql = '{}/bin/psql'.format(config.PG_LATEST)
    tpch_path = '{}/tpch_2_13_0/distributed_queries/'.format(config.TESTS_REPO)

    for query_code, executor_type in query_info:
        executor_string = "set citus.task_executor_type to '{}'".format(executor_type)
        enable_repartition_joins = "set citus.enable_repartition_joins to 'on'"
        run_string = '{} {} -c "{}" -c "{}" -c "\\timing" -f "{}"'.format(psql, connectionURI,
            enable_repartition_joins, executor_string, tpch_path + query_code)
        out_val = run(run_string)
        results_file.write(out_val)
        results_file.write('\n')

# If no citus valgrind logs exist results directory, then simply put valgrind_success 
# file under results directory.
def valgrind_filter_put_results():
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
        run('mv {} {}'.format(regression_diffs_path, config.RESULTS_DIRECTORY))

    # filter the (possibly) citus-related outputs and put to results file if existz

    if os.path.isfile(valgrind_logs_path):
        
        # get stack trace id that includes calls to citus
        run('cat {} | grep -i "citus" | awk \'{{ print $1 }}\' | uniq  > {}'.format(valgrind_logs_path, trace_ids_path))

        if os.path.isfile(trace_ids_path) and os.path.getsize(trace_ids_path) > 0:            
            # filter stack traces with stack trace ids that we found above (if any)
            run('while read line; do grep {} -e $line ; done < {} > {}'.format(
                valgrind_logs_path, 
                trace_ids_path,
                citus_valgrind_logs_path))
        
        # cleanup
        run('rm {}'.format(trace_ids_path))
    
    # if we have no citus-related valgrind outputs then just put an empty file named as `config.VALGRIND_SUCCESS_FNAME`
    if not os.path.exists(citus_valgrind_logs_path):    
        run('touch {}'.format(success_file_path))

def valgrind_internal(valgrind_target):
    'Runs valgrind tests'

    # set citus path variable
    repo_path = config.settings[config.REPO_PATH]
    
    use.valgrind()
    setup.valgrind()

    with cd(os.path.join(repo_path, config.RELATIVE_REGRESS_PATH)):

        # make check-multi-vg returns 2 in case of failures in regression tests
        # we should do failure handling here
        with settings(warn_only=True):
            valgrind_logs_path=os.path.join(config.RESULTS_DIRECTORY, config.VALGRIND_LOGS_FILE)
            valgrind_test_out_path = os.path.join(config.RESULTS_DIRECTORY, config.VALGRIND_TEST_OUT_FILE)

            # wrap the command with tee to log stdout & stderr to a file in results directory as well
            # this is done to ensure that valgrind test is actually finished
            valgrind_test_command = 'CITUS_VALGRIND_LOG_FILE={} make {}'.format(valgrind_logs_path, valgrind_target)
            valgrind_test_command = valgrind_test_command + ' 2>&1 | tee {}'.format(valgrind_test_out_path)

            run(valgrind_test_command)

            valgrind_filter_put_results()

@task
@roles('master')
def valgrind(*args):
    'Choose a valgrind target. For example: fab ... run.valgrind:check-multi-1-vg ...'

    available_valgrind_targets = ('check-multi-vg', 'check-multi-1-vg', 'check-columnar-vg')
    if len(args) != 1 or args[0] not in available_valgrind_targets:
        abort('Only a single argument for run.valgrind is available: {}'.
              format(', '.join(available_valgrind_targets)))
    
    valgrind_target = args[0]
    valgrind_internal(valgrind_target)
