-- Fact table: 1 แถว = 1 รีวิว
--
-- `category` ติดมาด้วยในฐานะ degenerate dimension (ซ้ำกับที่อยู่ใน dim_product)
-- เพราะตอน export เป็น Parquet เราแบ่ง partition ด้วยคอลัมน์นี้ ผู้ใช้ปลายทาง
-- จะได้อ่านทีละหมวดโดยไม่ต้องสแกนทั้งไฟล์
--
-- ข้อความรีวิวแยกไปอยู่ marts.review_text (join ด้วย review_id) เพื่อให้ตาราง
-- fact เล็กพอโหลดเข้า pandas บนโน้ตบุ๊กได้

CREATE OR REPLACE TABLE marts.fact_review AS
SELECT
    r.review_id,
    CAST(strftime(r.review_date, '%Y%m%d') AS INTEGER) AS date_key,
    p.product_key,
    u.user_key,
    b.brand_key,
    c.category_key,
    rs.reviewer_segment_key,
    r.category,
    r.rating,
    r.helpful_vote,
    r.verified_purchase,
    r.has_images,
    (r.rating >= 4) AS is_positive,
    (r.rating <= 2) AS is_negative,
    r.review_ts
FROM staging.stg_reviews r
LEFT JOIN marts.dim_product p USING (parent_asin)
LEFT JOIN marts.dim_user u USING (user_id)
LEFT JOIN marts.dim_brand b
       ON b.brand_name = p.store
LEFT JOIN marts.dim_category c
       ON c.main_category = p.main_category AND c.parent_category = p.category
LEFT JOIN marts.dim_reviewer_segment rs
       ON rs.reviewer_segment = u.reviewer_segment;

-- ข้อความรีวิว "ดิบ" ยังไม่ทำความสะอาด — stage preprocessing จะมารับช่วงต่อ
CREATE OR REPLACE TABLE marts.review_text AS
SELECT
    review_id,
    category,
    parent_asin,
    rating,
    review_title,
    review_text
FROM staging.stg_reviews;
