import os.path

from fabric.api import task, cd, path, run, runs_once, roles, sudo

import utils
import config
import prefix

__all__ = [
    'session_analytics', 'hll', 'cstore', 'tpch', 'jdbc', 'shard_rebalancer'
]

@task
def session_analytics(*args):
    'Adds the session_analytics extension to the instance in pg-latest'
    prefix.check_for_pg_latest()

    # TODO: Requires hstore, do we install it automatically?
    utils.add_github_to_known_hosts() # make sure ssh doesn't prompt
    repo = config.paths['session-repo']
    latest = config.paths['pg-latest']

    if len(args) == 0:
        git_ref = 'master'
    else:
        git_ref = args[0]

    run('rm -rf {} || true'.format(repo)) # -f because git write-protects files
    run('git clone -q git@github.com:citusdata/session_analytics.git {}'.format(repo))
    with cd(repo), path('{}/bin'.format(latest)):
        run('git checkout {}'.format(git_ref))
        run('make install')

    # TODO: What if the server isn't running?
    with cd(latest):
        run('bin/psql -c "CREATE EXTENSION session_analytics;"')

@task
def hll():
    'Adds the hll extension to the instance in pg-latest'
    prefix.check_for_pg_latest()

    repo = config.paths['hll-repo']
    url = 'https://github.com/aggregateknowledge/postgresql-hll.git'

    run('rm -rf {} || true'.format(repo))
    run('git clone -q {} {}'.format(url, repo))
    with cd(repo), path('{}/bin'.format(config.paths['pg-latest'])):
        run('git checkout {}'.format(config.settings['hll-ref']))
        run('make install')

    with cd(config.paths['pg-latest']):
        run('bin/psql -c "CREATE EXTENSION hll"')

@task
def cstore():
    'Adds the cstore extension to the instance in pg-latest'
    prefix.check_for_pg_latest()

    sudo('yum install -q -y protobuf-c-devel')

    repo = config.paths['cstore-repo']
    url = 'https://github.com/citusdata/cstore_fdw.git'

    utils.rmdir(repo, force=True)
    run('git clone -q {} {}'.format(url, repo))
    with cd(repo), path('{}/bin'.format(config.paths['pg-latest'])):
        run('make install')

    with cd(config.paths['pg-latest']):
        run('bin/psql -c "CREATE EXTENSION cstore_fdw"')

@task
def shard_rebalancer():
    'Adds the shard rebalancer extension to pg-latest (requires enterprise)'
    prefix.check_for_pg_latest()

    repo = config.paths['rebalancer-repo']
    url = 'git@github.com:citusdata/shard_rebalancer.git'

    utils.rmdir(repo, force=True)
    run('git clone -q {} {}'.format(url, repo))
    with cd(repo), path('{}/bin'.format(config.paths['pg-latest'])):
        run('make install')

    with cd(config.paths['pg-latest']):
        run('bin/psql -c "CREATE EXTENSION shard_rebalancer"')

@task
@roles('master')
def tpch(**kwargs):
    'Generates and loads tpc-h data into the instance at pg-latest'
    prefix.check_for_pg_latest()

    latest = config.paths['pg-latest']

    scale = kwargs.get('scale-factor', 10)

    # generate tpc-h data
    tpch_path = '{}/tpch_2_13_0'.format(config.paths['tests-repo'])
    with cd(tpch_path):
        run('make')
        run('SCALE_FACTOR={} CHUNKS="o 24 c 4 P 1 S 4 s 1" sh generate2.sh'.format(scale))

        # create the tpc-h tables
        run('{}/bin/psql -f tpch_create_tables.ddl'.format(latest))

        # stage tpc-h data
        sed = r'''sed "s/\(.*\)\.tbl.*/\\\\COPY \1 FROM '\0' WITH DELIMITER '|'/"'''
        xargs = r'''xargs -d '\n' -L 1 -P 4 sh -c '{}/bin/psql -h localhost -c "$0"' '''.format(latest)

        for segment in run('find {} -name \'*.tbl*\''.format(tpch_path)).splitlines():
            table_name = os.path.basename(segment).split('.')[0]
            run('''{}/bin/psql -c "COPY {} FROM '{}' WITH DELIMITER '|'"'''.format(latest, table_name, segment))

@task
@roles('master')
def jdbc():
    'Adds everything required to test out the jdbc connecter'
    sudo('yum install -q -y java-1.6.0-openjdk-devel') # we only need java on the master
