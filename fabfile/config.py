from os.path import expanduser
import os

IS_SSH_KEYS_USED ='is_ssh_keys_used'
HOME_DIR = expanduser("~")

CODE_DIRECTORY = os.path.join(HOME_DIR, 'code')
TESTS_REPO = os.path.join(HOME_DIR, 'test-automation')
CITUS_REPO = os.path.join(HOME_DIR, 'citus')
ENTERPRISE_REPO = os.path.join(HOME_DIR, 'citus-enterprise')
PG_LATEST = os.path.join(HOME_DIR, 'pg-latest')
PG_SOURCE_BALLS = os.path.join(HOME_DIR, 'postgres-source')
HOME_DIRECTORY = HOME_DIR
RESULTS_DIRECTORY = os.path.join(HOME_DIR, 'results')
CITUS_INSTALLATION = os.path.join(HOME_DIR, 'citus-installation')
PORT = 5432

PG_VERSION = '9.6.1'
PG_CONFIGURE_FLAGS = ['--with-openssl --enable-debug']
PG_CFLAGS = ['-ggdb -g3']

settings = {
    IS_SSH_KEYS_USED: True
}
