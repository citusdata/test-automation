from fabric.api import task, run, cd, runs_once, roles

import config
import utils

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
@roles('master')
def tpch_queries():
    'Runs selected tpch queries'

    tpch_file_list = ['tpch_1', 'tpch_3', 'tpch_5', 'tpch_6', 'tpch_7', 'tpch_8', 'tpch_9', 'tpch_10', 'tpch_12', 'tpch_14', 'tpch_19']

    for tpch_file in tpch_file_list:
    	utils.psql_file('$HOME/test-automation/tpch_queries/' + tpch_file + '.sql')
