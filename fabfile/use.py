'''
This namespace doesn't perform any installation, it's only used to change configuration
which later tasks read. The "citus" task, for instance, specifies which git ref to use
when building Citus.
'''
import re

from fabric.api import task, runs_once, abort, local, lcd

import config
import utils

@task
@runs_once
def citus(*args):
    'Choose a citus version. For example: fab use.citus:v6.0.1 setup.basic_testing (defaults to master)'

    # Do a local checkout to make sure this is a valid ref
    # (so we error as fast as possible)

    if len(args) != 1:
        abort('You must provide a single argument, with a command such as "citus:v6.0.1"')
    git_ref = args[0]

    path = config.paths['citus-repo']
    local('rm -rf {} || true'.format(path))
    local('git clone -q https://github.com/citusdata/citus.git {}'.format(path))
    with lcd(path):
        local('git checkout {}'.format(git_ref))
    local('rm -rf {} || true'.format(path))

    config.settings['citus-git-ref'] = git_ref

@task
@runs_once
def postgres(*args):
    'Choose a postgres version. For example: fab use.postgres:9.6.1 setup.basic_testing'

    if len(args) != 1:
        abort('You must provide a single argument. For example: "postgres:9.6.1"')
    version = args[0]
    if not re.match(utils.postgres_version_regex, version):
        abort('"{}" is not a valid postgres version. Enter something like "9.6.1"'.format(version))

    config.settings['pg-version'] = version
    utils.download_pg() # Check that this doesn't 404

@task
@runs_once
def asserts(*args):
    'Enable asserts in pg (and therefore citus)'
    config.settings['pg-configure-flags'].append('--enable-cassert')

@task
@runs_once
def debug_mode(*args):
    '''ps's configure is passed: '--enable-debug --enable-cassert CFLAGS="-ggdb -Og -g3 -fno-omit-frame-pointer"' '''
    config.settings['pg-configure-flags'].append('--enable-debug --enable-cassert CFLAGS="-ggdb -Og -g3 -fno-omit-frame-pointer"')
