from invoke import task
from invoke.exceptions import Exit

from connection import master, workers, all_nodes # connections to nodes but no tasks
import config # settings, but no tasks
import pg  # tasks which control postgres
import add  # tasks which add things to existing clusters
import setup  # tasks which create clusters with preset settings
import use  # tasks which change some configuration future tasks read
import run  # tasks to run misc commands
import prefix  # utilities for keeping track of where we're installing everything

# control the output of "fab --list"
__all__ = ['pg', 'add', 'setup', 'use', 'run', 'set_pg_latest', 'main']

@task(default=True)
def main():
    'The default task (what happens when you type "fab"), currently setup.basic_testing'
    setup.basic_testing(master)

@task
def set_pg_latest(*args):
    'Use this if you want multiple simultaneous installs, the README has more information'

    if len(args) != 1:
        raise Exit('You must provide an argument. Such as: "set_prefix:${HOME}/prefix"')
    new_prefix = args[0]

    prefix.set_prefix(all_nodes, new_prefix)

@task
def dummy(c):
    c.run('echo dummy')
