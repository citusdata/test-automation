#!/bin/bash

set -euo pipefail

# check n args
if [ "$#" -ne 4 ]; then
    echo "Usage: $0 <PG_VERSION> <CITUS_VERSION> <TEST_SCHEDULE> <ARTIFACTS_DIR>"
    exit 1
fi

PG_VERSION=$1
CITUS_VERSION=$2
TEST_SCHEDULE=$3
ARTIFACTS_DIR=$4

image_name="citus-vg-$PG_VERSION-$CITUS_VERSION"

docker build . -t "$image_name" --build-arg PG_VERSION="$PG_VERSION" --build-arg CITUS_VERSION="$CITUS_VERSION"

container_name="$image_name-$TEST_SCHEDULE-$(date +"%Y-%m-%d-%H-%M-%S")"

test_artifacts_dir="$ARTIFACTS_DIR/$container_name"
mkdir -p "$test_artifacts_dir"

# determine make target based on the test schedule
if [[ "$TEST_SCHEDULE" == *"failure"* ]]; then
    make_check_target="check-failure-custom-schedule-vg"
elif [[ "$TEST_SCHEDULE" == *"isolation"* ]]; then
    make_check_target="check-isolation-custom-schedule-vg"
else
    make_check_target="check-custom-schedule-vg"
fi

# At this point, we don't want to fail copying the artifacts if the container run
# or a prior copy fails, so we disable exit-on-error.
set +e

docker run --name "$container_name" "$image_name" bash -c "export PATH=/pgenv/pgsql/bin/:$PATH && SCHEDULE=$TEST_SCHEDULE make -C /citus/src/test/regress/ $make_check_target"

docker cp "$container_name":/citus/src/test/regress/regression.diffs "$test_artifacts_dir/"
docker cp "$container_name":/citus/src/test/regress/regression.out "$test_artifacts_dir/"
docker cp "$container_name":/citus/src/test/regress/citus_valgrind_test_log.txt "$test_artifacts_dir/"
