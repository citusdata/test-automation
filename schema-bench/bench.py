#!/usr/bin/env python3

import fire
from psycopg import sql
from psycopg_pool import AsyncConnectionPool
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


class Bench:
    async def build(
        self,
        scale=100,
        table_count=10,
        concurrency=multiprocessing.cpu_count(),
        connection_string="",
    ):
        async with AsyncConnectionPool(
            connection_string,
            min_size=concurrency,
            kwargs=dict(prepare_threshold=None, autocommit=True),
        ) as pool:
            self.pool = pool
            tasks = []
            for i in range(scale):
                tasks.append(self.create_schema(i, table_count))
            await asyncio.gather(*tasks)

    async def create_schema(self, index, table_count):
        async with self.pool.connection() as conn:
            schema_string = f"schema_bench_{index}"
            schema = sql.Identifier(schema_string)
            await conn.execute(
                sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                    schema,
                )
            )
            await conn.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
            for j in range(table_count):
                table = sql.Identifier(schema_string, f"table_{j}")
                await conn.execute(
                    sql.SQL(
                        "CREATE TABLE {}(id bigserial PRIMARY KEY, data text, number bigint)"
                    ).format(table)
                )

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
