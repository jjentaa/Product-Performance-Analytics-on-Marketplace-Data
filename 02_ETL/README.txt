02_ETL — โค้ด ELT + Preprocessing
===================================

โฟลเดอร์นี้คือสำเนาโค้ดจาก repository หลัก (path เดิม: elt/ และ preprocessing/)
รันจาก root ของ repository หลักเท่านั้น (โค้ดอ้างอิง path แบบ relative to
project root ผ่าน config.yaml)

elt/            สคริปต์ ELT — extract (ดาวน์โหลดจาก Hugging Face),
                load (เข้า DuckDB schema raw), transform (SQL ใน elt/sql/,
                raw -> staging -> star schema), export (Parquet),
                publish (ขึ้น Hugging Face)
elt/sql/        SQL ที่สร้าง staging + star schema (dim_date, dim_product,
                dim_user, fact_review, review_text) + quality checks
preprocessing/  Notebook สำรวจข้อมูล (exploration.ipynb) และ preprocessing
                pipeline (preprocessing.ipynb) — ล้างข้อความ, สร้าง feature,
                แบ่ง train/val/test

วิธีรัน (จาก root ของ repository หลัก)
------------------------------------------
  pip install -r requirements.txt
  python -m elt.run_elt        # extract -> load -> transform -> export
  python -m elt.publish        # push ขึ้น Hugging Face (ต้อง login ก่อน)
  # แล้วเปิด preprocessing/preprocessing.ipynb รัน Run All

รายละเอียดขั้นตอน+เครื่องมือทั้งหมด: ดู README.pdf (หัวข้อ 7)
