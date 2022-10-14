'''
A grab bag of functions used by other modules
'''

import os.path
import os
import socket

from patchwork.files import append, exists
from invoke.exceptions import Exit

import config

# TODO:: this can be replaced with makedirs(..., exists_ok=True) when we upgrade to python3
def mkdir_if_not_exists(path):
    if not os.path.exists(path):
        os.mkdir(path)


def rmdir(c, path, force=False):
    'Better than rm because it is silent when the file does not exist'
    flag = '-f' if force else ''
    if exists(c, path):
        c.run('rm {} -r {}'.format(flag, path))


def psql(c, command='', filepath='', connectionURI=''):
    if command == '' and filepath == '':
        raise Exit('psql needs at least one of the -c or -f options!')

    with c.cd(config.PG_LATEST):
        psql_command = 'bin/psql {} '.format(connectionURI)

        if command != '':
            psql_command += '-c "{}" '.format(command)
        if filepath != '':
            psql_command += '-f {} '.format(filepath)
        return c.run(psql_command)


def add_github_to_known_hosts(c):
    'Removes prompts from github checkouts asking whether you want to trust the remote'
    key = 'github.com ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ=='
    append(c, os.path.join(config.HOME_DIR, '.ssh/known_hosts'), key)


def download_pg(c):
    "Idempotent, does not download if file already exists. Returns the file's location"
    version = config.PG_VERSION
    url = pg_url_for_version(version)

    target_dir = config.PG_SOURCE_BALLS
    c.run('mkdir -p {}'.format(target_dir))

    target_file = '{}/{}'.format(target_dir, os.path.basename(url))

    if exists(c, target_file):
        return target_file

    c.run('wget -O {} --no-verbose {}'.format(target_file, url))
    return target_file

def pg_contrib_dir():
    version = config.PG_VERSION
    src_dir = os.path.join(config.PG_SOURCE_BALLS, 'postgresql-{}'.format(version))
    contrib_dir = os.path.join(src_dir, 'contrib')
    return contrib_dir

def pg_url_for_version(version):
    return 'https://ftp.postgresql.org/pub/source/v{0}/postgresql-{0}.tar.bz2'.format(version)

def get_local_ip():
    return socket.gethostbyname(socket.gethostname())

def get_preload_libs_string(preloaded_libs):
    return "shared_preload_libraries = \'{}\'".format(",".join(preloaded_libs))

def get_core_count():
    core_count = os.cpu_count()
    return core_count
