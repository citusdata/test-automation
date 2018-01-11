\set aid  random(1, 100000)
\set bid  random(1, 100000)
INSERT INTO test_table_target SELECT * FROM test_table WHERE  key = :aid OR key =:bid LIMIT 10;
