from fabric.api import task, run, cd, runs_once

@task
@runs_once
def jdbc():
    'Assumes add.jdbc and add.tpch have been run'
    with cd('/home/ec2-user/test-automation/jdbc'):
        run('javac JDBCReleaseTest.java')
        run('java -classpath postgresql-9.4.1212.jre6.jar:. JDBCReleaseTest')
