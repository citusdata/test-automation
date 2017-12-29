\set aid  random(1, 100000)
SELECT count(*) FROM test_table WHERE key = :aid;