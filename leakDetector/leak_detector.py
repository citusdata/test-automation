#!/usr/bin/env python2

import subprocess
import time
import sys
import os
from threading import Thread

MONITOR_INTERVAL_IN_SECS = 20
MONITOR_TIME_IN_SECS = 200

def get_memory_usage_of_process(pid):
    ps = subprocess.Popen(('pmap', str(pid)), stdout=subprocess.PIPE)
    total_memory = subprocess.check_output(('grep', 'total'), stdin=ps.stdout)
    ps.wait()
    return total_memory

def monitor_memory_usage_of_process(pid, time_in_secs):
    f = open('memory_usage_{}.out'.format(pid), 'a')

    start_in_secs = get_curtime_in_seconds()
    passed_time_in_secs  = 0 

    while passed_time_in_secs < time_in_secs:
        passed_time_in_secs = get_curtime_in_seconds() - start_in_secs
        total_memory = get_memory_usage_of_process(pid)
        f.write('memory usage in {} seconds: {}'.format(passed_time_in_secs, total_memory))
        time.sleep(MONITOR_INTERVAL_IN_SECS)
    
    f.close()


def get_curtime_in_seconds():
    return int(round(time.time()))   

def psql(port, file):
    file = os.path.abspath(file)
    subprocess.call([
        'psql',
        '-p', port,
        '-f', file
        ])

def psql_background(port, file):
    file = os.path.abspath(file)
    proc = subprocess.Popen([
        'psql',
        '-p', port,
        '-f', file
    ])
    print(proc.pid)
    return proc.pid

def pgbench(port, file, thread_count, time):
    file = os.path.abspath(file)
    subprocess.call([
        'pgbench',
        '-p', port,
        '-f', file,
        '-c', str(thread_count),
        '-j', str(thread_count),
        '-T', str(time)
    ])

if __name__ == '__main__':

    coordinator_port = sys.argv[1]
    worker_port = sys.argv[2]
    init_file = sys.argv[3]
    query_file = sys.argv[4]


    psql(coordinator_port, init_file)
    psql_pid = psql_background(worker_port, query_file)

    monitor_thread = Thread(target= monitor_memory_usage_of_process, args= (psql_pid, MONITOR_TIME_IN_SECS ))
    monitor_thread.start()

    # pgbench(coordinator_port, query_file, 1, time_in_secs)
    monitor_thread.join()
