'''
$HOME/pg-latest (config.PG_LATEST) should always point to the
installation of citus we're currently working with. This way tasks which interact with an
installation can just use pg-latest and not care where it points to. (We use this instead
of something like a "use" task because this is long-term state which should be kept
between invocations of fab)
'''
import os.path

from invoke.exceptions import Exit
from patchwork.files import exists

import config

def set_prefix(c, prefix):
    'Change where pg-latest points to'

    if not os.path.isabs(prefix):
        raise Exit('{} is not an absolute path'.format(prefix))

    latest = config.PG_LATEST

    # -f to overwrite any existing links
    # -n to not follow the {latest} link, if it exists, and instead replace it
    c.run('ln -snf {} {}'.format(prefix, latest))
    c.run('mkdir -p {}'.format(prefix))

def ensure_pg_latest_exists(c, default):
    'If there is no valid working directory make one and point it at prefix'
    latest = config.PG_LATEST

    # make sure pg-latest exists
    if not exists(c, latest):
        set_prefix(c, default)

    # make sure pg-latest is a link
    if c.run('stat -c %F {}'.format(latest)).stdout.strip() != 'symbolic link':
        raise Exit('pg-latest exists but is not a symbolic link!')

    # make sure the link points to something
    destination = c.run('readlink {}'.format(latest)).stdout.strip()
    c.run('mkdir -p {}'.format(destination))

def check_for_pg_latest(c):
    "Fail-fast if there isn't a valid working directory"
    latest = config.PG_LATEST

    if not exists(c, latest):
        raise Exit('There is no pg-latest symlink, run a setup.XXX task to create a cluster or the set-pg-latest task to point pg-latest to a citus installation')

    destination = c.run('readlink {}'.format(latest)).stdout.strip()

    if not exists(c, destination):
        raise Exit('pg-latest does not point to a valid working directory, run a setup.XXX task to create a cluster')
