from fabric.api import task, run, cd

from config import paths

@task
def start():
    'Start the database in pg-latest'
    with cd(paths['pg-latest']):
        # "set -m" spawns postgres in a new process group so it runs in the background
        run('set -m; bin/pg_ctl -D data -l logfile start')

@task
def stop():
    'Stop the database in pg-latest'
    with cd(paths['pg-latest']):
        run('set -m; bin/pg_ctl -D data stop')

@task
def restart():
    'Restart the database in pg-latest'
    with cd(paths['pg-latest']):
        run('set -m; bin/pg_ctl -D data restart')
