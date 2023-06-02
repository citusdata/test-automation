#!/usr/bin/env python3

import fire
import psycopg
from psycopg import sql
from psycopg_pool import AsyncConnectionPool, ConnectionPool
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from functools import partial
from itertools import repeat
import multiprocessing
import asyncio
import sys
import subprocess
import tempfile


def eprint(*args, **kwargs):
    """eprint prints to stderr"""

    print(*args, file=sys.stderr, **kwargs)


def run(command, *args, check=True, shell=True, silent=False, **kwargs):
    """run runs the given command and prints it to stderr"""

    if not silent:
        eprint(f"+ {command} ")
    if silent:
        kwargs.setdefault("stdout", subprocess.DEVNULL)
    return subprocess.run(command, *args, check=check, shell=shell, **kwargs)


def capture(command, *args, **kwargs):
    """runs the given command and returns its output as a string"""
    return run(command, *args, stdout=subprocess.PIPE, text=True, **kwargs).stdout


def create_schemas(args):
    connection_string = args[0]
    table_count = args[1]
    indexes = args[2]

    with psycopg.connect(
        connection_string, prepare_threshold=None, autocommit=True
    ) as conn:
        for i in indexes:
            schema_string = f"schema_bench_{i}"
            schema = sql.Identifier(schema_string)
            conn.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    schema,
                )
            )
            conn.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
            for j in range(table_count):
                table = sql.Identifier(schema_string, f"table_{j}")
                conn.execute(
                    sql.SQL(
                        "CREATE TABLE {}(id bigserial PRIMARY KEY, data text, number bigint)"
                    ).format(table)
                )


def chunkify(l, n):
    """Yield n number of striped chunks from l."""
    return [l[i::n] for i in range(n)]


class Bench:
    def build(
        self,
        scale=100,
        table_count=10,
        concurrency=multiprocessing.cpu_count(),
        connection_string="",
    ):
        chunks = chunkify(list(range(scale)), concurrency)
        print(chunks)
        with ProcessPoolExecutor(
            max_workers=concurrency,
        ) as executor:
            for _ in executor.map(
                create_schemas,
                zip(repeat(connection_string), repeat(table_count), chunks)
            ):
                pass

    def run(
        self,
        scale=100,
        table_count=10,
        connection_string="",
        client=multiprocessing.cpu_count(),
        jobs=multiprocessing.cpu_count(),
        time=5,
        progress=5,
    ):
        with tempfile.NamedTemporaryFile("w") as f:
            f.write(
                f"""
                \\set schemaid random(0, {scale - 1})
                \\set tableid random(0, {table_count - 1})
                SELECT data, number FROM schema_bench_:schemaid.table_:tableid WHERE id = 1;
                """,
            )
            print(f.name)
            f.flush()

            run(
                [
                    "pgbench",
                    "--file",
                    f.name,
                    "--client",
                    str(client),
                    "--jobs",
                    str(jobs),
                    "--time",
                    str(time),
                    "--progress",
                    str(progress),
                    connection_string,
                ],
                shell=False,
            )


if __name__ == "__main__":
    fire.Fire(Bench)
