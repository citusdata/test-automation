-- table with some random source data
CREATE TABLE t (a int, b int, c double precision);

INSERT INTO t SELECT 10 * random(), 10 * random(), random()
                FROM generate_series(1,10000000);

-- table with pre-aggregated digests into table "p"
CREATE TABLE p AS SELECT a, b, tdigest(c, 100) AS d FROM t GROUP BY a, b;
SELECT create_distributed_table('p','a');

-- summarize the data from "p" (compute the 95-th percentile)
SELECT a, tdigest_percentile(d, 0.95) FROM p GROUP BY a ORDER BY a;

-- exact results
SELECT a, percentile_cont(0.95) WITHIN GROUP (ORDER BY c)
  FROM t GROUP BY a ORDER BY a;

-- tdigest estimate (no parallelism)
SET max_parallel_workers_per_gather = 0;
SELECT a, tdigest_percentile(c, 100, 0.95) FROM t GROUP BY a ORDER BY a;

-- tdigest estimate (4 workers)
SET max_parallel_workers_per_gather = 4;
SELECT a, tdigest_percentile(c, 100, 0.95) FROM t GROUP BY a ORDER BY a;