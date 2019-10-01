from os.path import expanduser
import os

HOME_DIR = expanduser("~")

paths = {
    'code-directory': os.path.join(HOME_DIR, 'code'),
    'tests-repo': os.path.join(HOME_DIR, 'test-automation'),
    'citus-repo': os.path.join(HOME_DIR, 'citus'),
    'enterprise-repo': os.path.join(HOME_DIR, 'citus-enterprise'),
    'pg-latest': os.path.join(HOME_DIR, 'pg-latest'),
    'pg-source-balls': os.path.join(HOME_DIR, 'postgres-source'),
    'home-directory': HOME_DIR, 
    'citus-installation': os.path.join(HOME_DIR, 'citus-installation')
}

settings = {
    'pg-version': '9.6.1',
    'pg-configure-flags': ['--with-openssl'],
}
