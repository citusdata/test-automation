from os.path import expanduser

HOME_DIR = expanduser("~")

paths = {
    'code-directory': HOME_DIR + '/code',
    'tests-repo': HOME_DIR + '/test-automation',
    'citus-repo': HOME_DIR + '/citus',
    'enterprise-repo': HOME_DIR + '/citus-enterprise',
    'pg-latest': HOME_DIR + '/pg-latest',
    'pg-source-balls': HOME_DIR + '/postgres-source',
    'home-directory': HOME_DIR, 
    'citus-installation': HOME_DIR + '/citus-installation'
}

settings = {
    'pg-version': '9.6.1',
    'pg-configure-flags': ['--with-openssl'],
}
