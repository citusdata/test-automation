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

# For each core file that valgrind generated in case of a process crash (if any),
# we run gdb and save the backtrace to a file.
if [ -f /citus/src/test/regress/citus_valgrind_test_log.txt.core.* ]; then
    pushd /citus/src/test/regress/

    mkdir gdb_core_backtraces

    for core_file_name in ./citus_valgrind_test_log.txt.core.*; do
        gdb -ex bt -ex quit postgres $core_file_name &> gdb_core_backtraces/$core_file_name
    done

    echo "Found core files. Stacktraces are saved under /citus/src/test/regress/gdb_core_backtraces."
    echo "Stacktraces will be copied back to the host machine as artifacts but you might want to further investigate the core files."

    popd
fi
