from invoke import task

import config
import prefix
from utils import psql


__all__ = ['start', 'stop', 'restart', 'read_config', 'set_config', 'set_config_str']


@task
def start(c):
    'Start the database in pg-latest'
    prefix.check_for_pg_latest(c)

    with c.cd(config.PG_LATEST):
        # "set -m" spawns postgres in a new process group so it runs in the background
        c.run('set -m; bin/pg_ctl --timeout=1000 -D data -l logfile start')


@task
def stop(c):
    'Stop the database in pg-latest'
    prefix.check_for_pg_latest(c)

    with c.cd(config.PG_LATEST):
        c.run('set -m; bin/pg_ctl -D data stop')


@task
def restart(c):
    'Restart the database in pg-latest'
    prefix.check_for_pg_latest(c)

    with c.cd(config.PG_LATEST):
        c.run('set -m; bin/pg_ctl -D data -l logfile restart')

        # TODO: Maybe also check that the server started properly. And if it didn't tail the log file?


@task
def read_config(c, key):
    'Returns the present value of the requested key e.x `fab pg.read_config:max_connections`'
    prefix.check_for_pg_latest(c)

    psql(c, 'SHOW {}'.format(key))


@task
def set_config(c, key, value):
    'Changes the postgres configuration: e.g. `fab pg.set_config:max_connections,200`'
    prefix.check_for_pg_latest(c)

    psql(c, 'ALTER SYSTEM SET {} TO {}'.format(key, value))


@task
def set_config_str(c, config):
    prefix.check_for_pg_latest(c)

    psql(c, 'ALTER SYSTEM SET {}'.format(config))
