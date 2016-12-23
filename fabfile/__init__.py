from fabric.api import env, task, execute, runs_once

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
import run

@task(default=True)
@runs_once
def main():
    execute(setup.basic_testing)
