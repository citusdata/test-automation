'''
This namespace doesn't perform any installation, it's only used to change configuration
which later tasks read. The "citus" task, for instance, specifies which git ref to use
when building Citus.
'''
import re

from invoke import task
from invoke.exceptions import Exit
import setup

import config
import utils

__all__ = ['citus', 'enterprise', 'postgres', 'hammerdb', 'asserts', 'debug_mode', 'valgrind']

@task
def citus(c, *args):
    'Choose a citus version. For example: fab use.citus:v6.0.1 setup.basic_testing (defaults to master)'

    # Do a local checkout to make sure this is a valid ref
    # (so we error as fast as possible)

    if len(args) != 1:
        raise Exit('You must provide a single argument, with a command such as "use.citus:v6.0.1"')
    git_ref = args[0]

    # set community repo specific variables
    config.settings[config.REPO_PATH] = config.CITUS_REPO
    config.settings[config.BUILD_CITUS_FUNC] = setup.build_citus

    # check if we can clone citus successfully, then remove it
    path = "/tmp/tmp_citus"
    c.local('rm -rf {} || true'.format(path))
    c.local('git clone -q https://github.com/citusdata/citus.git {}'.format(path))
    with c.lcd(path):
        c.local('git checkout {}'.format(git_ref))
    c.local('rm -rf {} || true'.format(path))

    config.settings['citus-git-ref'] = git_ref

@task
def enterprise(c, *args):
    'Choose a citus enterprise version. For example: fab use.enterprise:v6.0.1 setup.enterprise (defaults to enterprise-master)'

    # Do a local checkout to make sure this is a valid ref
    # (so we error as fast as possible)
    utils.add_github_to_known_hosts(c) # make sure ssh doesn't prompt
    if len(args) != 1:
        raise Exit('You must provide a single argument, with a command such as "use.enterprise:v6.0.1"')
    git_ref = args[0]

    # set enterprise repo specific variables
    config.settings[config.REPO_PATH] = config.ENTERPRISE_REPO
    config.settings[config.BUILD_CITUS_FUNC] = setup.build_enterprise

    # check if we can clone citus successfully, then remove it
    path = "/tmp/tmp_citus"
    c.local('rm -rf {} || true'.format(path))
    if config.settings[config.IS_SSH_KEYS_USED]:
        c.local('git clone -q git@github.com:citusdata/citus-enterprise.git {}'.format(path))
    else:
        c.local('git clone -q https://github.com/citusdata/citus-enterprise.git {}'.format(path))
    with c.lcd(path):
        c.local('git checkout {}'.format(git_ref))
    c.local('rm -rf {} || true'.format(path))

    config.settings['citus-git-ref'] = git_ref

@task
def postgres(c, *args):
    'Choose a postgres version. For example: fab use.postgres:9.6.1 setup.basic_testing'

    if len(args) != 1:
        raise Exit('You must provide a single argument. For example: "postgres:9.6.1"')
    version = args[0]

    config.PG_VERSION = version
    utils.download_pg(c) # Check that this doesn't 404

@task
def hammerdb(c, *args):
    # we use git tokens for authentication in hammerdb
    config.settings[config.IS_SSH_KEYS_USED] = False

@task
def asserts(c, *args):
    'Enable asserts in pg (and therefore citus) by passing --enable-cassert'
    config.PG_CONFIGURE_FLAGS.append('--enable-cassert')

@task
def debug_mode(c, *args):
    '''ps's configure is passed: '--enable-debug --enable-cassert CFLAGS="-ggdb -Og -g3 -fno-omit-frame-pointer"' '''
    config.PG_CONFIGURE_FLAGS.append('--enable-debug --enable-cassert CFLAGS="-ggdb -Og -g3 -fno-omit-frame-pointer"')


@task
def valgrind(c, *args):
    config.PG_CONFIGURE_FLAGS.append('--with-icu --enable-cassert --enable-debug CFLAGS="-ggdb -Og -DUSE_VALGRIND"')
    