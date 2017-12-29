\set aid  random(1, 100000)
\set bid  random(1, 100000)
\set cid  random(1, 100000)
\set did  random(1, 100000)

INSERT INTO test_table (key, value_1, value_2, value_3, value_4) VALUES
    ((:aid)::int, NULL, NULL, NULL, NULL),
    ((:bid)::int, NULL, NULL, NULL, NULL),
    ((:cid)::int, NULL, NULL, NULL, NULL),
    ((:did)::int, NULL, NULL, NULL, NULL);
