\set aid  random(1, 100000)
\set bid  random(1, 100000)
\set cid  random(1, 100000)
\set did  random(1, 100000)
UPDATE test_table SET value_1 =  row_to_json(row(:aid,:bid, row(:cid+10, :did+500,:aid *7), row(:cid-10, :did-500,:aid *71))) WHERE key = :aid;
