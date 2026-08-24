03_Data_Warehouse — Star Schema
==================================

Engine: DuckDB (query ตรงบนไฟล์ Parquet ไม่ต้องมี server)
Grain ของ fact table: 1 แถว = 1 รีวิว

ไฟล์ในโฟลเดอร์นี้
--------------------
star_schema.svg / star_schema.drawio   ER diagram (drawio แก้ไขได้ที่
                                        app.diagrams.net)
business_questions.md                  คำถามธุรกิจ 10 ข้อ + SQL ที่รันได้จริง
10_staging.sql ... 40_quality_checks.sql   SQL ที่สร้าง schema นี้จริง
                                        (raw -> staging -> star schema
                                        + quality checks)
sample_tables/                         ตัวอย่างข้อมูลจริงจากแต่ละตาราง
                                        (50-100 แถวแรก) ให้ดูโครงสร้าง/
                                        ค่าจริงโดยไม่ต้องรัน pipeline

ทำไมไม่แนบข้อมูลเต็ม
-----------------------
Warehouse ฉบับเต็มมี fact_review 3,658,936 แถว และ dim_product 998,708 แถว
(รวมเป็น Parquet ~535 MB) ใหญ่เกินจะแนบใน submission ข้อมูลเต็มอยู่บน
Hugging Face แบบ public เข้าถึงได้ทันทีโดยไม่ต้องใช้ token:

  Dataset #1 (star schema)      : huggingface.co/datasets/Madnesss/amazon-beauty-star-schema
  Dataset #2 (พร้อมเทรนโมเดล)   : huggingface.co/datasets/Madnesss/amazon-beauty-analytics-ready

โหลดใช้ทันทีด้วย:
  import pandas as pd
  fact = pd.read_parquet("hf://datasets/Madnesss/amazon-beauty-star-schema/fact_review")

รายละเอียด schema เต็ม (คำอธิบายทุกคอลัมน์): ดู README.pdf หัวข้อ 6
