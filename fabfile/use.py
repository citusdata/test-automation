'''
This namespace doesn't perform any installation, it's only used to change configuration
which later tasks read. The "citus" task, for instance, specifies which git ref to use
when building Citus.
'''
from invoke import task

import setup
import config
import multi_connections
import utils

@task(positional=['version'])
def citus(c, version):
    'Choose a citus version. For example: fab use.citus v11.1.5 setup.basic-testing (defaults to master)'
    if multi_connections.execute_on_all_nodes_if_no_hosts(c, citus, version):
        return

    git_ref = version

    # set community repo specific variables
    config.settings[config.REPO_PATH] = config.CITUS_REPO
    config.settings[config.BUILD_CITUS_FUNC] = setup.build_citus

    # check if we can clone citus successfully, then remove it
    path = "/tmp/tmp_citus"
    c.run('rm -rf {} || true'.format(path))
    c.run('git clone -q https://github.com/citusdata/citus.git {}'.format(path))
    c.run('cd {} && git checkout {}'.format(path, git_ref))
    c.run('rm -rf {} || true'.format(path))

    config.settings['citus-git-ref'] = git_ref

@task(positional=['version'])
def postgres(c, version):
    'Choose a postgres version. For example: fab use.postgres 9.6.1 setup.basic-testing'
    if multi_connections.execute_on_all_nodes_if_no_hosts(c, postgres, version):
        return

    config.PG_VERSION = version
    utils.download_pg(c) # Check that this doesn't 404

@task
def hammerdb(c):
    # we use git tokens for authentication in hammerdb
    if multi_connections.execute_on_all_nodes_if_no_hosts(c, hammerdb):
        return

    config.settings[config.IS_SSH_KEYS_USED] = False

@task
def asserts(c):
    'Enable asserts in pg (and therefore citus) by passing --enable-cassert'
    if multi_connections.execute_on_all_nodes_if_no_hosts(c, asserts):
        return

    config.PG_CONFIGURE_FLAGS.append('--enable-cassert')

@task
def debug_mode(c):
    '''ps's configure is passed: '--enable-debug --enable-cassert CFLAGS="-ggdb -Og -g3 -fno-omit-frame-pointer"' '''
    if multi_connections.execute_on_all_nodes_if_no_hosts(c, debug_mode):
        return

    config.PG_CONFIGURE_FLAGS.append('--enable-debug --enable-cassert CFLAGS="-ggdb -Og -g3 -fno-omit-frame-pointer"')

@task
def valgrind(c):
    if multi_connections.execute_on_all_nodes_if_no_hosts(c, valgrind):
        return

    config.PG_CONFIGURE_FLAGS.append('--with-icu --enable-cassert --enable-debug CFLAGS="-ggdb -Og -DUSE_VALGRIND"')
