import os.path

from fabric.api import task, runs_once, abort, run
from fabric.contrib.files import exists

import config

@task
def set_prefix(prefix):
    'Change where pg-latest points to'

    if not os.path.isabs(prefix):
        abort('{} is not an absolute path'.format(prefix))

    latest = config.paths['pg-latest']

    run('rm {1} && ln -s {0} {1}'.format(prefix, latest))

def ensure_pg_latest_exists(prefix):
    'If there is no valid working directory make one'
    latest = config.paths['pg-latest']

    if not exists(latest):
        set_prefix(prefix)

def check_for_pg_latest():
    "Fail-fast if there isn't a valid working directory"
    latest = config.paths['pg-latest']

    if not exists(latest):
        abort('There is no pg-latest symlink, run a setup.XXX task to create a cluster or the set_pg_latest task to point pg-latest to a citus installation')

    destination = run('readlink {}'.format(latest))

    if not exists(destination):
        abort('pg-latest does not point to a valid working directory, run a setup.XXX task to create a cluster')
