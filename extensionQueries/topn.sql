CREATE TABLE customer_reviews
(
    customer_id TEXT,
    review_date DATE,
    review_rating INTEGER,
    review_votes INTEGER,
    review_helpful_votes INTEGER,
    product_id CHAR(10),
    product_title TEXT,
    product_sales_rank BIGINT,
    product_group TEXT,
    product_category TEXT,
    product_subcategory TEXT,
    similar_product_ids CHAR(10)[]
);

--\COPY customer_reviews FROM 'data/customer_reviews_2000.csv' WITH CSV;

-- Create a roll-up table to capture most popular products
CREATE TABLE popular_products
(
  review_date date UNIQUE,
  agg_data jsonb
);

-- Create different summaries by grouping top reviews for each date (day, month, year)
INSERT INTO popular_products
    SELECT review_date, topn_add_agg(product_id)
    FROM customer_reviews
    GROUP BY review_date;
SELECT create_distributed_table('popular_products','review_date');

-- QUERIES --
SELECT review_date, (topn(agg_data, 1)).*
FROM popular_products
ORDER BY review_date;

SELECT (topn(topn_union_agg(agg_data), 10)).*
FROM popular_products
WHERE review_date >= '2000-01-01' AND review_date < '2000-02-01'
ORDER BY 2 DESC;

SELECT date_trunc('month', review_date) AS review_month,
       (topn(topn_union_agg(agg_data), 1)).*
FROM popular_products
WHERE review_date >= '2000-01-01' AND review_date < '2001-01-01'
GROUP BY review_month
ORDER BY review_month;