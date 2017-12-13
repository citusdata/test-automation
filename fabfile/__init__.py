from fabric.api import env, task, execute, runs_once, abort

def mess_with_roledefs(environment):
    '''
    For some reason -R and -H and, by default, lowest in the order of precedence.

    This method attempts to put them somewhere in the middle.

    If -R and -H are not specified, tasks will be run on all machines.
    -R and -H can be used to only run tasks on the given roles or hosts, respectively.
    If a task uses the @roles decorator, that task will always be run on the nodes in that
      role, regardless of what was passed into -H or -R.

    TODO: This means that any tasks with @roles('workers') will fail to take into account
    -H and instead run on all workers.

    TODO: There's a strong chance this interacts badly with --exclude-hosts
    '''
    if environment.roles and environment.hosts:
        abort('Specifying both a role and a host to use is not supported.')

    environment.roledefs = {
        'master': ['localhost'],
        'workers': [ip.strip() for ip in open('worker-instances')],
    }

    if environment.hosts or environment.roles:
        return

    environment.roles = ['master', 'workers']

mess_with_roledefs(env)

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
    setup.basic_testing()

@task
@runs_once
def set_pg_latest(*args):
    'Use this if you want multiple simultaneous installs, the README has more information'

    if len(args) != 1:
        abort('You must provide an argument. Such as: "set_prefix:/home/ec2-user/prefix"')
    new_prefix = args[0]

    execute(prefix.set_prefix, new_prefix)
