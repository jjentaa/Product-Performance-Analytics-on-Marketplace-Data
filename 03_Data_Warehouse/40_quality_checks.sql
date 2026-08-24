-- ตรวจคุณภาพข้อมูล — ทำเป็น view เพื่อให้ทั้ง export และ notebook เรียกใช้ได้
-- แถวไหน status = 'FAIL' คือปัญหาจริง ขั้น export จะไม่ยอมเขียนไฟล์ออก

CREATE OR REPLACE VIEW marts.v_quality_checks AS
WITH checks AS (
    SELECT 'fact rows with no product' AS check_name,
           count(*) AS bad_rows FROM marts.fact_review WHERE product_key IS NULL
    UNION ALL SELECT 'fact rows with no user',
           count(*) FROM marts.fact_review WHERE user_key IS NULL
    UNION ALL SELECT 'fact rows with no date',
           count(*) FROM marts.fact_review WHERE date_key IS NULL
    UNION ALL SELECT 'fact date_key not in dim_date',
           count(*) FROM marts.fact_review f ANTI JOIN marts.dim_date d USING (date_key)
    UNION ALL SELECT 'duplicate review_id in fact',
           coalesce(sum(n - 1), 0) FROM (
               SELECT count(*) AS n FROM marts.fact_review GROUP BY review_id HAVING count(*) > 1)
    UNION ALL SELECT 'duplicate product_key in dim_product',
           coalesce(sum(n - 1), 0) FROM (
               SELECT count(*) AS n FROM marts.dim_product GROUP BY product_key HAVING count(*) > 1)
    UNION ALL SELECT 'duplicate user_key in dim_user',
           coalesce(sum(n - 1), 0) FROM (
               SELECT count(*) AS n FROM marts.dim_user GROUP BY user_key HAVING count(*) > 1)
    UNION ALL SELECT 'ratings outside 1-5',
           count(*) FROM marts.fact_review WHERE rating NOT BETWEEN 1 AND 5
    UNION ALL SELECT 'negative helpful votes',
           count(*) FROM marts.fact_review WHERE helpful_vote < 0
    UNION ALL SELECT 'review_text rows not in fact',
           count(*) FROM marts.review_text t ANTI JOIN marts.fact_review f USING (review_id)
)
SELECT check_name, bad_rows,
       CASE WHEN bad_rows = 0 THEN 'PASS' ELSE 'FAIL' END AS status
FROM checks;

-- สรุปรายหมวด ใช้เขียนลง dataset card
CREATE OR REPLACE VIEW marts.v_category_summary AS
SELECT
    f.category,
    count(*)                                AS n_reviews,
    count(DISTINCT f.product_key)           AS n_products,
    count(DISTINCT f.user_key)              AS n_users,
    round(avg(f.rating), 2)                 AS avg_rating,
    round(avg(f.verified_purchase::INT), 3) AS verified_share,
    min(CAST(f.review_ts AS DATE))          AS first_review,
    max(CAST(f.review_ts AS DATE))          AS last_review
FROM marts.fact_review f
GROUP BY f.category
ORDER BY n_reviews DESC;
