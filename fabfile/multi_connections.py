from fabric import Connection
from invoke import Context
from invoke.exceptions import Exit

from connection import all_connections

def is_coordinator_connection(c):
    # returns true if the connection is to local node or it is a context object(no connection to localhost sometimes).
    # Info: specifying -H flag(hostlist) will pass the @task a Connection object. if -H is not specified a Context object will be passed.

    if isinstance(c, Connection):
        return c.host == 'localhost'
    elif isinstance(c, Context):
        return True
    raise Exit('Unexpected connection!')

def name_of_connection(c):
    if isinstance(c, Connection):
        return "{}:{}".format(c.host, c.port)
    elif isinstance(c, Context):
        return 'localhost'
    raise Exit('Unexpected connection!')

def execute_on_all_nodes_if_no_hosts(c, task, *args, **kwargs):
    # fab <task> will execute on only on local node but we modify it to execute on all nodes.
    # that method should be called in the first line of each @task if we want to have explained behaviour.

    # no -H is given if the connection is of Context (fab <task>)
    if isinstance(c, Context) and not isinstance(c, Connection) and len(all_connections) > 1:
        execute(all_connections, task, *args, **kwargs)
        return True
    return False

def execute(connections, task, *args, **kwargs):
    # runs a task on given connections

    for connection in connections:
        task(connection, *args, **kwargs)
