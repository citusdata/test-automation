\set aid random(1, 100000 * 100)
SELECT abalance FROM pgbench_accounts WHERE aid = :aid;
