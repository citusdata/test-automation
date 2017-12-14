\set aid random(1, 10000000)
UPDATE test_table SET b = :aid WHERE a = :aid;

