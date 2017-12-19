\set aid  random(1, 100000)
\set bid  random(1, 100000)
\set cid  random(1, 100000)
\set did  random(1, 100000)

INSERT INTO test_table (key, value_1, value_2, value_3, value_4) VALUES
						 (:aid,
						  row_to_json(row(:aid,:bid, row(:cid+10, :did+500,:aid *7), row(:cid-10, :did-500,:aid *71))),
						  ARRAY[:aid::text, :bid::text, :cid::text, :did::text, 'Onder Kalaci', 'CitusData Rocks']::text[],
						  int4range(:aid, :aid + :bid),
						  (:aid, :did)::complex);
