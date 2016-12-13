from fabric.api import run, env, cd, roles, task, parallel, execute
from fabric.operations import sudo

# TODO: For each worker node, add it on the master node

env.roledefs = {
    'master': ['localhost'],
    'workers': [ip.strip() for ip in open('worker-instances')],
}
env.roles = ['master', 'workers']

@task
def basic_testing():
    prefix = '/home/ec2-user/pg-961'

    # use sequential executes to make sure all nodes are setup before we
    # attempt to call master_add_node

    execute(common_setup, prefix)
    execute(add_workers, prefix)

@parallel
def common_setup(prefix):
    redhat_install_packages()
    build_postgres_96(prefix)
    build_citus(prefix)
    create_database(prefix)
    start_database(prefix)
    setup_database(prefix)

@roles('master')
def add_workers(prefix):
    with cd(prefix):
        for ip in env.roledefs['workers']:
            command = 'SELECT master_add_node(\'{}\', 5432);'.format(ip)
            run('bin/psql -c "{}"'.format(command))

def workers():
    'Reads the list of workers'
    for ip in open('worker-instances'):
        env.hosts.append(ip)

def master():
    env.hosts.append('localhost')

def all():
    workers()
    master()

def redhat_install_packages():
    # you can detect amazon linux with /etc/issue and redhat with /etc/redhat-release
    # TODO: are you sure -q works and is sufficient?
    sudo('yum groupinstall -q -y \'Development Tools\'')
    sudo('yum install -q -y libxml2-devel libxslt-devel'
         ' openssl-devel pam-devel readline-devel git')

def postgres_95():
    'Installs postges 9.5 from source'

    # Fetched from: https://ftp.postgresql.org/pub/source/v9.5.5/postgresql-9.5.5.tar.bz2
    postgres_url = 'https://s3.amazonaws.com/citus-deployment/aws/test-cluster/postgresql-9.5.5.tar.bz2'
    operations.get(postgres_url)

def build_postgres_96(prefix):
    'Installs postges 9.6 from source'
    # TODO: This might be more efficient if we download it locally and operations.put()
    # the file to the remote nodes

    # Fetched from https://ftp.postgresql.org/pub/source/v9.6.1/postgresql-9.6.1.tar.bz2
    postgres_url = 'https://s3.amazonaws.com/citus-deployment/aws/test-cluster/postgresql-9.6.1.tar.bz2'

    # -N means we'll check timestamps before overwriting the file, more importantly it
    # means we won't save this file as postgresql-9.5.5.tar.bz2.1 if it already exists
    run('wget -N --no-verbose {}'.format(postgres_url))

    # rm makes this idempotent, if not a bit inefficient
    run('rm -r postgresql-9.6.1 || true')
    run('tar -xf postgresql-9.6.1.tar.bz2')
    with cd('postgresql-9.6.1'):
        run('./configure --prefix={}'.format(prefix))
        run('make install')

def build_citus(prefix):
    run('rm -r citus || true')
    run('git clone -q https://github.com/citusdata/citus.git')
    with cd('citus'):
        run('PG_CONFIG={}/bin/pg_config ./configure'.format(prefix))
        run('make install')

def create_database(prefix):
    with cd(prefix):
        run('bin/initdb -D data')
    with cd('{}/data'.format(prefix)):
        run('echo "shared_preload_libraries = \'citus\'" >> postgresql.conf')
        run('echo "max_prepared_transactions = 100" >> postgresql.conf')

def start_database(prefix):
    with cd(prefix):
        # "set -m" makes sure postgres is spawned in a new process group and keeps running
        run('set -m; bin/pg_ctl -D data -l logfile start')

def setup_database(prefix):
    with cd(prefix):
        run('bin/createdb $(whoami)')
        run('bin/psql -c "CREATE EXTENSION citus;"')

def uname():
    run('uname -a')
