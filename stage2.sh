#!/bin/sh

export MASTER_HOSTNAME=${MASTER_HOSTNAME:-localhost}
export NUM_PROCS=${NUM_PROCS:-4}
export PGUSER=${PGUSER:-ec2-user}

# This command lists all the <table name>.tbl.<shard number> files in the current
# directory and translates their names to \STAGE <table name> FROM '<file name>'...
# The stage commands are passed to psql and executed in parallel.

ls *.tbl* | sed "s/\(.*\)\.tbl.*/\\\\STAGE \1 FROM '\0' WITH DELIMITER '|'/" | xargs -d '\n' -L 1 -P $NUM_PROCS sh -c '/opt/citusdb/3.0/bin/psql -h $MASTER_HOSTNAME -d postgres -U $PGUSER -c "$0"'
/opt/citusdb/3.0/bin/psql -h localhost -d postgres -U $PGUSER -c "ANALYZE;"
