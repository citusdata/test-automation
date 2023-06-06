\set aid  random_gaussian(1, 100000 * :scale, 4)

SELECT abalance FROM pgbench_accounts WHERE aid = :aid;