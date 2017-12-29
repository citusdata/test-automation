\set aid  random(1, 100000)
\set bid  random(1, 100000)
\set cid  random(1, 100000)
\set did  random(1, 100000)

INSERT INTO test_table (key, value_1, value_2, value_3, value_4) VALUES
						 (:aid,
						  row_to_json(row((:aid)::text, row(:cid-10, :did-500))),
						  ARRAY[:aid::text, 'CitusData Rocks']::text[],
						  int4range(:aid, :bid + 100000),
						  (:aid, :did)::complex);
