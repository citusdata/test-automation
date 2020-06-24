'''
This namespace doesn't perform any installation, it's only used to change configuration
which later tasks read. The "citus" task, for instance, specifies which git ref to use
when building Citus.
'''
import re

from fabric.api import task, runs_once, abort, local, lcd, roles

import config
import utils

@task
def citus(*args):
    'Choose a citus version. For example: fab use.citus:v6.0.1 setup.basic_testing (defaults to master)'

    # Do a local checkout to make sure this is a valid ref
    # (so we error as fast as possible)

    if len(args) != 1:
        abort('You must provide a single argument, with a command such as "use.citus:v6.0.1"')
    git_ref = args[0]

    path = config.CITUS_REPO
    local('rm -rf {} || true'.format(path))
    local('git clone -q https://github.com/citusdata/citus.git {}'.format(path))
    with lcd(path):
        local('git checkout {}'.format(git_ref))
    local('rm -rf {} || true'.format(path))

    config.settings['citus-git-ref'] = git_ref

@task
def enterprise(*args):
    'Choose a citus enterprise version. For example: fab use.enterprise:v6.0.1 setup.enterprise (defaults to enterprise-master)'

    # Do a local checkout to make sure this is a valid ref
    # (so we error as fast as possible)
    utils.add_github_to_known_hosts() # make sure ssh doesn't prompt
    if len(args) != 1:
        abort('You must provide a single argument, with a command such as "use.enterprise:v6.0.1"')
    git_ref = args[0]

    path = config.ENTERPRISE_REPO
    local('rm -rf {} || true'.format(path))
    if config.settings[config.IS_SSH_KEYS_USED]:
        local('git clone -q git@github.com:citusdata/citus-enterprise.git {}'.format(path))
    else:
        local('git clone -q https://github.com/citusdata/citus-enterprise.git {}'.format(path))
    with lcd(path):
        local('git checkout {}'.format(git_ref))
    local('rm -rf {} || true'.format(path))

    config.settings['citus-git-ref'] = git_ref

@task
@roles('master')
def postgres(*args):
    'Choose a postgres version. For example: fab use.postgres:9.6.1 setup.basic_testing'

    if len(args) != 1:
        abort('You must provide a single argument. For example: "postgres:9.6.1"')
    version = args[0]

    config.PG_VERSION = version
    utils.download_pg() # Check that this doesn't 404

@task
def hammerdb(*args):
    # we use git tokens for authentication in hammerdb
    config.settings[config.IS_SSH_KEYS_USED] = False

@task
def asserts(*args):
    'Enable asserts in pg (and therefore citus) by passing --enable-cassert'
    config.PG_CONFIGURE_FLAGS.append('--enable-cassert')

@task
def debug_mode(*args):
    '''
    pg's configure is passed: '--enable-debug --enable-cassert CFLAGS="-ggdb -g3 -Og -fno-omit-frame-pointer"' 
    Normally this does not contain --enable-cassert, -Og and
    -fno-omit-frame-pointer. The rest are default.
    '''
    config.PG_CONFIGURE_FLAGS.append('--enable-cassert')
    config.PG_CFLAGS.append('-Og -fno-omit-frame-pointer')
