from os.path import expanduser
import os

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
RELATIVE_REGRESS_PATH = 'src/test/regress'
COMMUNITY_REPO = 'community'
ENTERPRISE_REPO = 'enterprise'
# valgrind test variables
VALGRIND_LOGS_FILE = 'valgrind_logs.txt'
REGRESSION_DIFFS_FILE = 'regression.diffs'
CITUS_RELATED_VALGRIND_LOGS_FLE = 'valgrind_logs_citus_so.txt'

PG_VERSION = '9.6.1'
PG_CONFIGURE_FLAGS = ['--with-openssl']

settings = {

}
