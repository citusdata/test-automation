from invoke import task
from invoke import Collection

import multi_connections # multi_connections module implements some features on top of fabric
import prefix  # utilities for keeping track of where we're installing everything
from connection import all_connections # connections for nodes

import pg # tasks which control postgres
import add # tasks which add things to existing clusters
import setup # tasks which create clusters with preset settings
import use # tasks which change some configuration future tasks read
import run # tasks to run misc commands

@task(default=True)
def main(c):
    'The default task (what happens when you type "fab"), currently setup.basic-testing'
    if not multi_connections.is_coordinator_connection(c):
        return
    if multi_connections.execute_on_all_nodes_if_no_hosts(c, main):
        return

    setup.basic_testing(c)

@task(positional=['prefixpath'])
def set_pg_latest(c, prefixpath):
    'Use this if you want multiple simultaneous installs, the README has more information'
    if not multi_connections.is_coordinator_connection(c):
        return

    if multi_connections.execute_on_all_nodes_if_no_hosts(c, set_pg_latest, prefixpath):
        return

    new_prefix = prefixpath

    multi_connections.execute(all_connections, prefix.set_prefix, new_prefix)

# control the output of "fab --list"
def setup_tasks():
    ns = Collection('fabfile')
    ns.add_task(main)
    ns.add_task(set_pg_latest)
    ns.add_collection(pg)
    ns.add_collection(add)
    ns.add_collection(setup)
    ns.add_collection(use)
    ns.add_collection(run)
    return ns
ns = setup_tasks()
