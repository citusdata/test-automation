from os.path import expanduser
import os

IS_SSH_KEYS_USED ='is_ssh_keys_used'
HOME_DIR = expanduser("~")

CODE_DIRECTORY = os.path.join(HOME_DIR, 'code')
TEST_REPO = os.path.join(HOME_DIR, 'test-automation')
CITUS_REPO = os.path.join(HOME_DIR, 'citus')
ENTERPRISE_REPO = os.path.join(HOME_DIR, 'citus-enterprise')
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

# valgrind test variables
VALGRIND_TEST_OUT_FILE = 'valgrind_test_out.txt'
VALGRIND_LOGS_FILE = 'citus_valgrind_test_log.txt'
REGRESSION_DIFFS_FILE = 'regression.diffs'
CITUS_RELATED_VALGRIND_LOG_FILE = 'valgrind_test_log_citus.txt'
VALGRIND_REQUIRED_PACKAGES = ['valgrind', 'valgrind-devel.x86_64', 'openssl-devel.x86_64', 'libicu-devel.x86_64']
VALGRIND_SUCCESS_FNAME = 'valgrind_success'

PG_VERSION = '15.1'
PG_CONFIGURE_FLAGS = ['--with-openssl','--enable-tap-tests']

settings = {
    IS_SSH_KEYS_USED: True
}
