from fabric import Connection
from fabric.group import SerialGroup

import config

__all__ = ['master', 'workers', 'all_nodes']

master_ip = 'localhost'
worker_ips = [ip.strip() for ip in open(config.HOME_DIR + '/test-automation/worker-instances')]
master = Connection(master_ip, user="pguser", forward_agent=True, connect_kwargs={"key_filename": "/home/aykutbozkurt/.ssh/id_rsa",},)
workers = Connection("localhost")#SerialGroup(worker_ips, user="pguser", forward_agent=True,)
all_nodes = Connection("localhost")#SerialGroup([master_ip] + worker_ips, user="pguser", forward_agent=True,)
