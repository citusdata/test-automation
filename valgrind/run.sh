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

docker build -t "$image_name" --build-arg PG_VERSION="$PG_VERSION" --build-arg CITUS_VERSION="$CITUS_VERSION" docker/

container_name="$image_name-$TEST_SCHEDULE-$(date +"%Y-%m-%d-%H-%M-%S")"

test_artifacts_dir="$ARTIFACTS_DIR/$container_name"
mkdir -p "$test_artifacts_dir"

# determine make target based on the test schedule
if [[ "$TEST_SCHEDULE" == *"failure"* ]]; then
    # Actually, Citus repo supports failure schedules under valgrind via
    # "check-failure-custom-schedule-vg" but the Dockerfile we use for
    # valgrind doesn't yet have the necessary dependencies to run the
    # failure schedules.
    echo "failure schedules are not supported yet"
    exit 1
elif [[ "$TEST_SCHEDULE" == *"isolation"* ]]; then
    make_check_target="check-isolation-custom-schedule-vg"
else
    make_check_target="check-custom-schedule-vg"
fi

# At this point, we don't want to fail copying the artifacts if the container run
# or a prior copy fails, so we disable exit-on-error.
set +e

start_time=$(date +%s)

docker run --name "$container_name" "$image_name" /run_valgrind_test.sh "$TEST_SCHEDULE" "$make_check_target"

end_time=$(date +%s)

echo "Copying artifacts from container to host"

docker cp "$container_name":/citus/src/test/regress/regression.diffs "$test_artifacts_dir/"
docker cp "$container_name":/citus/src/test/regress/regression.out "$test_artifacts_dir/"
docker cp "$container_name":/citus/src/test/regress/citus_valgrind_test_log.txt "$test_artifacts_dir/"
docker cp "$container_name":/citus/src/test/regress/gdb_core_backtraces "$test_artifacts_dir/"

# finally, also dump some information about the test run
echo "PG_VERSION=$PG_VERSION" > "$test_artifacts_dir/meta"
echo "CITUS_VERSION=$CITUS_VERSION" >> "$test_artifacts_dir/meta"
echo "TEST_SCHEDULE=$TEST_SCHEDULE" >> "$test_artifacts_dir/meta"
echo "MAKE_CHECK_TARGET=$make_check_target" >> "$test_artifacts_dir/meta"
echo "IMAGE_NAME=$image_name" >> "$test_artifacts_dir/meta"
echo "CONTAINER_NAME=$container_name" >> "$test_artifacts_dir/meta"
echo "TIME_TAKEN_SEC=$((end_time - start_time))" >> "$test_artifacts_dir/meta"
