from fabric.api import task, cd, path, run, runs_once

from utils import add_github_to_known_hosts
import config

@task
def session_analytics(*args):
    'Adds the session_analytics extension to the instance in pg-latest'
    # TODO: Requires hstore, do we install it automatically?
    add_github_to_known_hosts() # make sure ssh doesn't prompt
    repo = config.paths['session-repo']
    prefix = config.paths['pg-latest']

    if len(args) == 0:
        git_ref = 'master'
    else:
        git_ref = args[0]

    run('rm -rf {} || true'.format(repo)) # -f because git write-protects files
    run('git clone -q git@github.com:citusdata/session_analytics.git {}'.format(repo))
    with cd(repo), path('{}/bin'.format(prefix)):
        run('git checkout {}'.format(git_ref))
        run('make install')

    # TODO: What if the server isn't running?
    with cd(prefix):
        run('bin/psql -c "CREATE EXTENSION session_analytics;"')

@task
def hll():
    'Adds the hll extension to the instance in pg-latest'
    repo = config.paths['hll-repo']
    url = 'https://github.com/aggregateknowledge/postgresql-hll.git'

    run('rm -rf {} || true'.format(repo))
    run('git clone -q {} {}'.format(url, repo))
    with cd(repo), path('{}/bin'.format(config.paths['pg-latest'])):
        run('git checkout {}'.format(config.settings['hll-ref']))
        run('make install')

    with cd(config.paths['pg-latest']):
        run('bin/psql -c "CREATE EXTENSION hll"')
