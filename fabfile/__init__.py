from fabric.api import env, task, execute, runs_once, abort

env.roledefs = {
    'master': ['localhost'],
    'workers': [ip.strip() for ip in open('worker-instances')],
}
env.roles = ['master', 'workers']
env.forward_agent = True # So remote machines can checkout private git repos

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
@runs_once
def main():
    'The default task (what happens when you type "fab"), currently setup.basic_testing'
    execute(setup.basic_testing)

@task
@runs_once
def set_pg_latest(*args):
    'Use this if you want multiple simultaneous installs, the README has more information'

    if len(args) != 1:
        abort('You must provide an argument. Such as: "set_prefix:/home/ec2-user/prefix"')
    new_prefix = args[0]

    execute(prefix.set_prefix, new_prefix)
