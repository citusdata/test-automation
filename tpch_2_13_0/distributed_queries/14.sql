-- Query #14
------------

SELECT
    100.00 * sum(case
        when p_type like 'PROMO%'
            then l_extendedprice * (1 - l_discount)
        else 0
    end) / sum(l_extendedprice * (1 - l_discount)) as promo_revenue
FROM
    lineitem,
    part
WHERE
    l_partkey = p_partkey
    AND l_shipdate >= date '1995-09-01'
    AND l_shipdate < date '1995-09-01' + interval '1' month
-- the following LIMIT is not part of the benchmark suite
-- but required to run the tests automatically
-- see https://github.com/citusdata/test-automation/issues/120    
LIMIT 4;    
