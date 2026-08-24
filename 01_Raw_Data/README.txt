01_Raw_Data — ข้อมูลดิบต้นทาง
================================

แหล่งข้อมูล
-----------
Amazon Reviews 2023 (McAuley Lab, UC San Diego)
https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023

หมวดที่ใช้ (3 หมวดย่อยของ Beauty & Personal Care)
--------------------------------------------------
  - All_Beauty                (~0.54 GB)
  - Amazon_Fashion             (~2.47 GB)
  - Health_and_Personal_Care   (~0.35 GB)
รวม ~3.36 GB (701,528 / 2,500,939 / 494,121 บรรทัดตามลำดับ ก่อนทำความสะอาด)

ทำไมไม่แนบไฟล์ดิบทั้งหมด
--------------------------
ไฟล์ต้นฉบับรวมกัน ~3.36 GB ไม่เหมาะกับการแนบใน submission หรือ git repository
โฟลเดอร์ sample/ ด้านล่างนี้จึงมีแค่ 20 บรรทัดแรกของแต่ละไฟล์ (รีวิว + metadata
ของแต่ละหมวด) ที่ตัดมาจากไฟล์จริงตรง ๆ (ไม่ได้แต่งขึ้น) เพื่อให้เห็นโครงสร้าง/
คอลัมน์ของข้อมูลดิบจริง

วิธีดาวน์โหลดข้อมูลเต็มด้วยตัวเอง
------------------------------------
  1. ติดตั้ง dependency: pip install -r requirements.txt
  2. รัน: python -m elt.extract
  (สคริปต์อยู่ที่ 02_ETL/elt/extract.py ในโฟลเดอร์นี้ หรือ elt/extract.py ใน
  repository หลัก — จะดาวน์โหลดจาก Hugging Face ให้อัตโนมัติ ใช้ resume ได้
  ถ้าเชื่อมต่อขาดระหว่างดาวน์โหลด)

คอลัมน์สำคัญของข้อมูลดิบ
--------------------------
ไฟล์รีวิว:    rating, title, text, images, asin, parent_asin, user_id,
              timestamp, helpful_vote, verified_purchase
ไฟล์ metadata: title, main_category, average_rating, rating_number, price,
              store, categories, details, parent_asin
