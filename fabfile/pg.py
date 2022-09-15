from invoke import task

import config
import multi_connections
import prefix
from utils import psql

@task
def create(c):
    'Create the database in pg-latest'
    if multi_connections.execute_on_all_nodes_if_no_hosts(c, create):
        return

    prefix.check_for_pg_latest(c)

    with c.cd(config.PG_LATEST):
        c.run('bin/initdb -D data')

@task
def start(c):
    'Start the database in pg-latest'
    if multi_connections.execute_on_all_nodes_if_no_hosts(c, start):
        return

    prefix.check_for_pg_latest(c)

    with c.cd(config.PG_LATEST):
        # "set -m" spawns postgres in a new process group so it runs in the background
        c.run('set -m; bin/pg_ctl --timeout=1000 -D data -l logfile start')

@task
def stop(c):
    'Stop the database in pg-latest'
    if multi_connections.execute_on_all_nodes_if_no_hosts(c, stop):
        return

    prefix.check_for_pg_latest(c)

    with c.cd(config.PG_LATEST):
        c.run('set -m; bin/pg_ctl -D data stop')

@task
def restart(c):
    'Restart the database in pg-latest'
    if multi_connections.execute_on_all_nodes_if_no_hosts(c, restart):
        return

    prefix.check_for_pg_latest(c)

    with c.cd(config.PG_LATEST):
        c.run('set -m; bin/pg_ctl -D data -l logfile restart')

        # TODO: Maybe also check that the server started properly. And if it didn't tail the log file?

@task(positional=['key'])
def read_config(c, key):
    'Returns the present value of the requested key e.x `fab pg.read-config max_connections`'
    if multi_connections.execute_on_all_nodes_if_no_hosts(c, read_config, key):
        return

    prefix.check_for_pg_latest(c)

    psql(c, 'SHOW {}'.format(key))

@task(positional=['key', 'value'])
def set_config(c, key, value):
    'Changes the postgres configuration: e.g. `fab pg.set-config max_connections 200`'
    if multi_connections.execute_on_all_nodes_if_no_hosts(c, set_config, key, value):
        return

    prefix.check_for_pg_latest(c)

    psql(c, 'ALTER SYSTEM SET {} TO {}'.format(key, value))

@task
def set_config_str(c, config):
    if multi_connections.execute_on_all_nodes_if_no_hosts(c, set_config_str, config):
        return

    prefix.check_for_pg_latest(c)

    psql(c, 'ALTER SYSTEM SET {}'.format(config))
