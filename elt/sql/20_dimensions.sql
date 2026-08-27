-- Dimension tables ของ star schema

CREATE SCHEMA IF NOT EXISTS marts;

-- dim_date: 1 แถวต่อ 1 วัน ครอบคลุมช่วงทั้งหมดที่มีรีวิว
CREATE OR REPLACE TABLE marts.dim_date AS
WITH bounds AS (
    SELECT min(review_date) AS d0, max(review_date) AS d1 FROM staging.stg_reviews
),
days AS (
    SELECT CAST(unnest(generate_series(
        CAST(d0 AS TIMESTAMP), CAST(d1 AS TIMESTAMP), INTERVAL 1 DAY
    )) AS DATE) AS d
    FROM bounds
)
SELECT
    CAST(strftime(d, '%Y%m%d') AS INTEGER) AS date_key,
    d                                      AS full_date,
    year(d)                                AS year,
    quarter(d)                             AS quarter,
    month(d)                               AS month,
    strftime(d, '%B')                      AS month_name,
    week(d)                                AS week_of_year,
    dayofweek(d)                           AS day_of_week,
    dayname(d)                             AS day_name,
    dayofweek(d) IN (0, 6)                 AS is_weekend
FROM days;

-- dim_product: สินค้าจาก metadata + แถว placeholder ของสินค้าที่มีรีวิว
-- แต่ไม่มี metadata เพื่อให้ทุกแถวใน fact join ติดเสมอ (ดูธง has_metadata)
CREATE OR REPLACE TABLE marts.dim_product AS
WITH known AS (
    SELECT parent_asin, product_title, main_category, store, price,
           listed_avg_rating, listed_rating_count, category, TRUE AS has_metadata
    FROM staging.stg_products
),
missing AS (
    SELECT DISTINCT
        r.parent_asin,
        NULL AS product_title, NULL AS main_category, NULL AS store, NULL AS price,
        NULL AS listed_avg_rating, NULL AS listed_rating_count,
        r.category, FALSE AS has_metadata
    FROM staging.stg_reviews r
    ANTI JOIN staging.stg_products p USING (parent_asin)
),
combined AS (
    SELECT * FROM known
    UNION ALL BY NAME
    SELECT * FROM missing
)
SELECT
    row_number() OVER (ORDER BY parent_asin) AS product_key,
    parent_asin,
    product_title,
    main_category,
    store,
    price,
    CASE
        WHEN price IS NULL THEN 'Unknown'
        WHEN price < 10    THEN 'Budget (<$10)'
        WHEN price < 25    THEN 'Low ($10-25)'
        WHEN price < 50    THEN 'Mid ($25-50)'
        WHEN price < 100   THEN 'High ($50-100)'
        ELSE                    'Premium ($100+)'
    END AS price_band,
    listed_avg_rating,
    listed_rating_count,
    category,
    has_metadata
FROM combined;

-- dim_user: 1 แถวต่อ 1 คนรีวิว สรุปพฤติกรรมจากประวัติ "ข้ามทุกหมวดที่โหลด"
CREATE OR REPLACE TABLE marts.dim_user AS
SELECT
    row_number() OVER (ORDER BY user_id)  AS user_key,
    user_id,
    count(*)                              AS lifetime_reviews,
    count(DISTINCT category)              AS categories_reviewed,
    round(avg(rating), 2)                 AS avg_rating_given,
    sum(helpful_vote)                     AS total_helpful_votes,
    round(avg(verified_purchase::INT), 2) AS verified_share,
    min(review_date)                      AS first_review_date,
    max(review_date)                      AS last_review_date,
    CASE
        WHEN count(*) >= 10 THEN 'Power reviewer'
        WHEN count(*) >= 3  THEN 'Regular'
        ELSE                     'One-off'
    END AS reviewer_segment
FROM staging.stg_reviews
GROUP BY user_id;

-- dim_brand: 1 แถวต่อ 1 แบรนด์ (store) — แยกออกจาก dim_product เพื่อไม่ให้ชื่อ
-- แบรนด์ซ้ำอยู่ในทุกแถวสินค้าของแบรนด์เดียวกัน (dim_product ยังเก็บ store ไว้
-- เหมือนเดิมด้วย เพื่อไม่ให้ query เดิมที่ join ตรงกับ dim_product พังกัน)
CREATE OR REPLACE TABLE marts.dim_brand AS
SELECT
    row_number() OVER (ORDER BY store) AS brand_key,
    store                               AS brand_name,
    count(*)                            AS n_products
FROM marts.dim_product
WHERE store IS NOT NULL
GROUP BY store;

-- dim_category: 1 แถวต่อ (main_category, category) — main_category คือหมวดย่อย
-- ละเอียดจริงจาก metadata Amazon (เช่น "Skin Care") ต่างจาก category ซึ่งเป็น
-- หมวดใหญ่ 3 หมวดที่ใช้ partition ไฟล์ (ดูคอลัมน์ parent_category)
CREATE OR REPLACE TABLE marts.dim_category AS
SELECT
    row_number() OVER (ORDER BY category, main_category) AS category_key,
    main_category,
    category                                              AS parent_category,
    count(*)                                              AS n_products
FROM marts.dim_product
WHERE main_category IS NOT NULL
GROUP BY category, main_category;

-- dim_reviewer_segment: lookup คงที่ 3 แถว ตามเกณฑ์เดียวกับที่ใช้แบ่งใน dim_user
-- (junk dimension) — แยกออกมาให้ fact join ตรงถึงกลุ่มผู้รีวิวได้โดยไม่ต้องผ่าน dim_user
CREATE OR REPLACE TABLE marts.dim_reviewer_segment (
    reviewer_segment_key INTEGER,
    reviewer_segment      VARCHAR,
    min_reviews           INTEGER,
    max_reviews           INTEGER,
    description            VARCHAR
);
INSERT INTO marts.dim_reviewer_segment VALUES
    (1, 'One-off',        0,  2,    'Reviewed 1-2 times total'),
    (2, 'Regular',        3,  9,    'Reviewed 3-9 times total'),
    (3, 'Power reviewer',  10, NULL, 'Reviewed 10+ times total');
