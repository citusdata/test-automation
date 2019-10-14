from os.path import expanduser
import os

HOME_DIR = expanduser("~")

CODE_DIRECTORY = 'code-directory'
TESTS_REPO = 'tests-repo'
CITUS_REPO = 'citus-repo'
ENTERPRISE_REPO = 'enterprise-repo'
PG_LATEST = 'pg-latest'
PG_SOURCE_BALLS = 'pg-source-balls'
HOME_DIRECTORY = 'home-directory'
RESULTS_DIRECTORY = 'results-directory'
CITUS_INSTALLATION = 'citus-installation'

PG_VERSION = 'pg-version'
PG_CONFIGURE_FLAGS = 'pg-configure-flags'

paths = {
    CODE_DIRECTORY: os.path.join(HOME_DIR, 'code'),
    TESTS_REPO: os.path.join(HOME_DIR, 'test-automation'),
    CITUS_REPO: os.path.join(HOME_DIR, 'citus'),
    ENTERPRISE_REPO: os.path.join(HOME_DIR, 'citus-enterprise'),
    PG_LATEST: os.path.join(HOME_DIR, 'pg-latest'),
    PG_SOURCE_BALLS: os.path.join(HOME_DIR, 'postgres-source'),
    HOME_DIRECTORY: HOME_DIR, 
    RESULTS_DIRECTORY: os.path.join(HOME_DIR, 'results'),
    CITUS_INSTALLATION: os.path.join(HOME_DIR, 'citus-installation')
}

settings = {
    PG_VERSION: '9.6.1',
    PG_CONFIGURE_FLAGS: ['--with-openssl'],
}
