#!/bin/bash

set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <TEST_SCHEDULE> <MAKE_CHECK_TARGET>"
    exit 1
fi

TEST_SCHEDULE=$1
MAKE_CHECK_TARGET=$2

export PATH=/pgenv/pgsql/bin/:$PATH

# allow valgrind to generate a coredump if a test crashes
ulimit -c unlimited

# At this point, we don't want to fail rest of the script if valgrind exits with
# an error, so we disable exit-on-error.
set +e

SCHEDULE=$TEST_SCHEDULE make -C /citus/src/test/regress/ $MAKE_CHECK_TARGET

shopt -s nullglob

# Copy the contents of each valgrind log file to valgrind_logs.txt
valgrind_log_files=(/citus/src/test/regress/citus_valgrind_test_log.txt.[0-9]+)
if (( ${#valgrind_log_files[@]} )); then
    touch /citus/src/test/regress/valgrind_logs.txt

    # for each file, print pid and then its content to  valgrind_logs.txt
    for valgrind_log_file in "${valgrind_log_files[@]}"; do
        echo "+++++++++++++++++++++++++ $(basename "$valgrind_log_file") +++++++++++++++++++++++++" >> /citus/src/test/regress/valgrind_logs.txt
        cat "$valgrind_log_file" >> /citus/src/test/regress/valgrind_logs.txt
        echo "" >> /citus/src/test/regress/valgrind_logs.txt
    done
fi

# For each core file that valgrind generated in case of a process crash (if any),
# we run gdb and save the backtrace to a file.
core_files=(/citus/src/test/regress/citus_valgrind_test_log.txt.core.[0-9]+)
if (( ${#core_files[@]} )); then
    pushd /citus/src/test/regress/

    mkdir gdb_core_backtraces

    for core_file_name in "${core_files[@]}"; do
        base_name=$(basename "$core_file_name")
        gdb -ex bt -ex quit postgres "$core_file_name" &> "gdb_core_backtraces/$base_name"
    done

    echo "Found core files. Stacktraces are saved under /citus/src/test/regress/gdb_core_backtraces."
    echo "Stacktraces will be copied back to the host machine as artifacts but you might want to further investigate the core files."

    popd
fi
