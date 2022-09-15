from fabric import Connection

import config
import os

# init configuration params for connections
forward_agent = True

master_host = 'localhost'
worker_hosts = [ip.strip() for ip in open(config.HOME_DIR + '/test-automation/worker-instances')]
all_hosts = [master_host] + worker_hosts

key_file_path = os.path.join(config.HOME_DIR, ".ssh/id_rsa")
connection_settings = {
    "look_for_keys": True,
    "key_filename": key_file_path,
}

# create connections for master and workers
master_connection = Connection(master_host, user="pguser", forward_agent=forward_agent, connect_kwargs=connection_settings,)
worker_connections = []
for worker_host in worker_hosts:
    worker_connection = Connection(worker_host, user="pguser", forward_agent=forward_agent, connect_kwargs=connection_settings,)
    worker_connections.append(worker_connection)
all_connections = [master_connection] + worker_connections
