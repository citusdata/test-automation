\set aid  random(1, 100000)
\set bid  random(1, 100000)
INSERT INTO test_table_target SELECT * FROM test_table WHERE  :bid < 1000;
