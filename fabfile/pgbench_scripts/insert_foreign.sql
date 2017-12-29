\set aid  random(1, 100000)
\set bid  random(1, 100000)
\set cid  random(1, 100000)

INSERT INTO test_table (key) VALUES (:aid) ON CONFLICT DO NOTHING;
INSERT INTO test_table_referencing VALUES (:aid, :bid, :cid + 10);