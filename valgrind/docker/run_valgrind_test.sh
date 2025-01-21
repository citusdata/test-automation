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

SCHEDULE=$TEST_SCHEDULE make -C /citus/src/test/regress/ $MAKE_CHECK_TARGET
