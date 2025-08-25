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

shopt -s extglob nullglob

# Collect all Valgrind log files into a single file (valgrind_logs.txt).
# Handles both formats:
#   - Older Citus versions: a single file named citus_valgrind_test_log.txt
#   - Newer Citus versions: one file per PID, e.g. citus_valgrind_test_log.txt.<pid>
valgrind_log_files=(/citus/src/test/regress/citus_valgrind_test_log.txt?(.+([0-9])))
if (( ${#valgrind_log_files[@]} )); then
    output=/citus/src/test/regress/valgrind_logs.txt
    touch "$output"  # truncate/create output file

    # For each log file, add a header with its name and then append its contents
    for valgrind_log_file in "${valgrind_log_files[@]}"; do
        echo "+++++++++++++++++++++++++ $(basename "$valgrind_log_file") +++++++++++++++++++++++++" >> "$output"
        cat "$valgrind_log_file" >> "$output"
        echo "" >> "$output"
    done
fi

# For each core file that valgrind generated in case of a process crash (if any),
# we run gdb and save the backtrace to a file.
core_files=(/citus/src/test/regress/citus_valgrind_test_log.txt.core.+([0-9]))
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
