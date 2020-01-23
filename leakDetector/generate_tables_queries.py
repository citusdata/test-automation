#!/usr/bin/env python2

import subprocess
import random


TABLE_PREFIX = "table"
SYNC_METADA_SQL = "select start_metadata_sync_to_node(nodename, nodeport) from pg_dist_node;"
CREATE_TABLE = "CREATE TABLE {}(a int, b int);"
DISTRIBUTE_TABLE = "SELECT create_distributed_table('{}', 'a');"
INSERT_INTO_TABLE = "INSERT INTO {} SELECT *,* FROM generate_series(1, {});"

SETTINGS = [
    "citus.replication_model TO 'streaming'",
    "citus.shard_count TO 128"
]
SETTING_STRING = "set {};"

MAX_QUERY_PER_PROCEDURE = 300
MAX_CALL_AMOUNT = 100000
MIN_TABLE_SIZE = 1000
MAX_TABLE_SIZE = 1000000
REPEAT_AMOUNT = 7
PROCEDURE_COUNT = 5
TABLE_COUNT = 5

PROCEDURE_PREFIX = "CREATE OR REPLACE PROCEDURE p_{}(id int) LANGUAGE plpgsql AS $fn$ \nBEGIN"
PROCEDURE_SUFFIX =  """
END;
$fn$;
"""

PROCEDURE_CALL_SQL = "CALL p_{}({});"
CREATE_FUNCTION = "select create_distributed_function('p_{}(INTEGER)', 'id');"

QUERIES = [
    "PERFORM count(*) FROM {} WHERE a = id;",
    "PERFORM count(*) FROM {} WHERE a = id AND false;",
    "UPDATE {} SET b = id WHERE a = id;",
    "INSERT INTO {} VALUES(id, id);",
    "PERFORM a as new_a FROM {} WHERE a = id;",
    "PERFORM count(*) FROM {} WHERE a = id LIMIT 3;",
    "PERFORM count(*) FROM {} WHERE a = id LIMIT 3 OFFSET 1;",
    "PERFORM a FROM {} WHERE a = id ORDER BY a DESC LIMIT 3 OFFSET 1;",
    "PERFORM a FROM {} WHERE a = id GROUP BY a ORDER BY a;",
    "PERFORM avg(b) FROM {} WHERE a = id GROUP BY a;",
    "PERFORM count(*) FROM {} WHERE a = id AND 1=0;"
    
]


def generate_tables(table_count, file):
    table_names = []
    for i in range(0, table_count):
        cur_table_tame = "{}_{}".format(TABLE_PREFIX, str(i))
        table_names.append(cur_table_tame)
    
    for table_name in table_names:
        create_table_sql = CREATE_TABLE.format(table_name)
        distribute_table_sql = DISTRIBUTE_TABLE.format(table_name)
        write_to_newline(file, create_table_sql)
        write_to_newline(file, distribute_table_sql)
        #psql(coordinator_port, create_table_sql)
        #psql(coordinator_port, distribute_table_sql)

    write_to_newline(file, "")

    for table_name in table_names:
        table_size = random.randint(MIN_TABLE_SIZE, MAX_TABLE_SIZE)
        insert_sql = INSERT_INTO_TABLE.format(table_name, table_size)
        write_to_newline(file, insert_sql)
        #psql(coordinator_port, insert_sql)    
    write_to_newline(file, "")
    return table_names    

def write_to_newline(file, line):
    file.write(line)
    file.write("\n")

def generate_procedures(procedure_count, table_names, file):
    for i in range(0, procedure_count):
        cur_procedure = PROCEDURE_PREFIX.format(i)
        query_count = random.randint(1, MAX_QUERY_PER_PROCEDURE)
        for i in range (0, query_count):
            cur_query = random.choice(QUERIES)
            cur_query = cur_query.format(random.choice(table_names))
            cur_procedure += "\n"
            cur_procedure += "      "
            cur_procedure += cur_query
        cur_procedure += "\n"
        cur_procedure += PROCEDURE_SUFFIX
        write_to_newline(file, cur_procedure)

def generate_procedure_calls(procedure_count, file):
    call_amount = random.randint(1, MAX_CALL_AMOUNT)
    for i in range (0, call_amount):
        value = random.randint(1, 100)
        procedure_index = random.randint(0, procedure_count-1)
        current_call = PROCEDURE_CALL_SQL.format(procedure_index, value)
        for i in range(0, REPEAT_AMOUNT):
            write_to_newline(file, current_call)

def write_settings(file):
    write_to_newline(file, SYNC_METADA_SQL)
    for setting in SETTINGS:
        write_to_newline(file, SETTING_STRING.format(setting))
    write_to_newline(file, "")    

def write_create_functions(procedure_count, file):
    for i in range(0, procedure_count):
        write_to_newline(file, CREATE_FUNCTION.format(str(i)))

def create_files():
    init_file = open("init.sql", "w")
    query_file = open("query.sql", "w")
    write_settings(init_file)
    table_names = generate_tables(TABLE_COUNT, init_file)
    generate_procedures(PROCEDURE_COUNT, table_names, init_file)
    generate_procedure_calls(PROCEDURE_COUNT, query_file)
    write_create_functions(PROCEDURE_COUNT, init_file)
    init_file.close()
    query_file.close()

create_files()