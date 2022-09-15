CREATE TABLE facts (
    date            date,
    user_id         integer,
    activity_type   smallint,
    referrer        varchar(255)
);
SELECT create_distributed_table('facts','date');

-- Create the destination table
CREATE TABLE daily_uniques (
    date            date UNIQUE,
    users           hll
);
SELECT create_distributed_table('daily_uniques','date');

-- Fill it with the aggregated unique statistics
INSERT INTO daily_uniques(date, users)
    SELECT date, hll_add_agg(hll_hash_integer(user_id))
    FROM facts
    GROUP BY 1;


-- QUERIES --
SELECT date, hll_cardinality(users) FROM daily_uniques;

SELECT date, hll_cardinality(users) FROM daily_uniques;

SELECT EXTRACT(MONTH FROM date) AS month, hll_cardinality(hll_union_agg(users))
FROM daily_uniques
WHERE date >= '2012-01-01' AND
      date <  '2013-01-01'
GROUP BY 1;

SELECT date, #hll_union_agg(users) OVER seven_days
FROM daily_uniques
WINDOW seven_days AS (ORDER BY date ASC ROWS 6 PRECEDING);

SELECT date, (#hll_union_agg(users) OVER two_days) - #users AS lost_uniques
FROM daily_uniques
WINDOW two_days AS (ORDER BY date ASC ROWS 1 PRECEDING);

SELECT date, hll_add_agg(hll_hash_integer(user_id))
FROM facts
GROUP BY 1;

SELECT EXTRACT(MONTH FROM date), hll_cardinality(hll_union_agg(users))
FROM daily_uniques
GROUP BY 1;

SELECT date, #hll_union_agg(users) OVER seven_days
FROM daily_uniques
WINDOW seven_days AS (ORDER BY date ASC ROWS 6 PRECEDING);