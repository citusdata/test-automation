from os.path import expanduser
import os

IS_SSH_KEYS_USED ='is_ssh_keys_used'
HOME_DIR = expanduser("~")

CODE_DIRECTORY = os.path.join(HOME_DIR, 'code')
TEST_REPO = os.path.join(HOME_DIR, 'test-automation')
CITUS_REPO = os.path.join(HOME_DIR, 'citus')
PG_LATEST = os.path.join(HOME_DIR, 'pg-latest')
PG_SOURCE_BALLS = os.path.join(HOME_DIR, 'postgres-source')
HOME_DIRECTORY = HOME_DIR
RESULTS_DIRECTORY = os.path.join(HOME_DIR, 'results')
POSTGRES_INSTALLATION = os.path.join(HOME_DIR, 'postgres-installation')
PORT = 5432
RELATIVE_REGRESS_PATH = 'src/test/regress'

# keys to access settings dictionary
REPO_PATH = 'repo_path'
BUILD_CITUS_FUNC = 'build_citus_func'

REGRESSION_DIFFS_FILE = 'regression.diffs'

PG_VERSION = '9.6.1'
PG_CONFIGURE_FLAGS = ['--with-openssl','--enable-tap-tests']

settings = {
    IS_SSH_KEYS_USED: True
}
