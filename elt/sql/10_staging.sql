-- Staging: กำหนด type, ลบข้อมูลซ้ำ, กรองแถวเสีย
--
-- ขั้นนี้ยัง "ไม่แตะข้อความรีวิว" — การล้าง HTML/entity และ feature engineering
-- ทั้งหมดยกไปทำที่ stage preprocessing เพื่อให้ dataset ของ ELT เป็นภาพที่
-- ใกล้เคียงต้นฉบับที่สุด (แค่จัดโครงสร้างให้เป็น star schema)

CREATE SCHEMA IF NOT EXISTS staging;

-- 1 แถว = 1 รีวิว, dedupe ด้วย (user_id, asin, timestamp)
-- หมายเหตุ: สินค้าที่อยู่หลายหมวดอาจมีรีวิวเดียวกันปรากฏในหลายไฟล์
-- การ dedupe จะยุบเหลือแถวเดียว จำนวนรายหมวดจึงต่ำกว่าจำนวนบรรทัดในไฟล์ดิบเล็กน้อย
CREATE OR REPLACE TABLE staging.stg_reviews AS
SELECT
    md5(
        coalesce(user_id, '?') || '|' ||
        coalesce(asin, '?') || '|' ||
        coalesce(CAST("timestamp" AS VARCHAR), '?')
    )                                              AS review_id,
    user_id,
    asin,
    parent_asin,
    rating,
    title                                          AS review_title,
    text                                           AS review_text,
    coalesce(json_array_length(images), 0) > 0     AS has_images,
    greatest(coalesce(helpful_vote, 0), 0)         AS helpful_vote,
    coalesce(verified_purchase, FALSE)             AS verified_purchase,
    to_timestamp("timestamp" / 1000)               AS review_ts,
    CAST(to_timestamp("timestamp" / 1000) AS DATE) AS review_date,
    source_category                                AS category
FROM raw.reviews
WHERE rating BETWEEN 1 AND 5          -- ตัด null และ rating นอกช่วง
  AND user_id IS NOT NULL
  AND parent_asin IS NOT NULL
  AND "timestamp" IS NOT NULL
  -- ข้อมูลจบที่ ก.ย. 2023 อะไรที่หลุดกรอบนี้ถือว่าเสีย
  AND to_timestamp("timestamp" / 1000)
      BETWEEN TIMESTAMP '1996-01-01' AND TIMESTAMP '2024-01-01'
QUALIFY row_number() OVER (
    PARTITION BY user_id, asin, "timestamp"
    ORDER BY helpful_vote DESC
) = 1;

-- 1 แถว = 1 สินค้า (parent_asin) สินค้าที่โผล่หลายหมวดเก็บอันที่มีรีวิวเยอะสุด
CREATE OR REPLACE TABLE staging.stg_products AS
SELECT
    parent_asin,
    title                            AS product_title,
    main_category,
    store,
    -- price เป็น string ในต้นทาง: "None", "14.99" และบางทีเป็นช่วงราคา
    CASE WHEN try_cast(price AS DOUBLE) BETWEEN 0.01 AND 100000
         THEN try_cast(price AS DOUBLE) END AS price,
    average_rating                   AS listed_avg_rating,
    rating_number                    AS listed_rating_count,
    source_category                  AS category
FROM raw.meta
WHERE parent_asin IS NOT NULL
QUALIFY row_number() OVER (
    PARTITION BY parent_asin
    ORDER BY rating_number DESC NULLS LAST
) = 1;
