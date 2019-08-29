'''
$HOME/pg-latest (config.paths['pg-latest']) should always point to the
installation of citus we're currently working with. This way tasks which interact with an
installation can just use pg-latest and not care where it points to. (We use this instead
of something like a "use" task because this is long-term state which should be kept
between invocations of fab)
'''
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

    # -f to overwrite any existing links
    # -n to not follow the {latest} link, if it exists, and instead replace it
    run('ln -snf {} {}'.format(prefix, latest))
    run('mkdir -p {}'.format(prefix))

def ensure_pg_latest_exists(default):
    'If there is no valid working directory make one and point it at prefix'
    latest = config.paths['pg-latest']

    # make sure pg-latest exists
    if not exists(latest):
        set_prefix(default)

    # make sure pg-latest is a link
    if run('stat -c %F {}'.format(latest)) != 'symbolic link':
        abort('pg-latest exists but is not a symbolic link!')

    # make sure the link points to something
    destination = run('readlink {}'.format(latest))
    run('mkdir -p {}'.format(destination))

def check_for_pg_latest():
    "Fail-fast if there isn't a valid working directory"
    latest = config.paths['pg-latest']

    if not exists(latest):
        abort('There is no pg-latest symlink, run a setup.XXX task to create a cluster or the set_pg_latest task to point pg-latest to a citus installation')

    destination = run('readlink {}'.format(latest))

    if not exists(destination):
        abort('pg-latest does not point to a valid working directory, run a setup.XXX task to create a cluster')
