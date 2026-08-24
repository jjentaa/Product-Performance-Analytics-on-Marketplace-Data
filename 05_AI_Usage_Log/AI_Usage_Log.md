# AI Usage Log

เครื่องมือ: **Claude (Anthropic)** ผ่าน **Claude Code** — ใช้ตลอดการพัฒนาโปรเจกต์
บันทึกนี้ละเอียดกว่าสรุปในหัวข้อ 10 ของ README.pdf โดยไล่ตามลำดับงานจริงที่เกิดขึ้น
พร้อมระบุจุดที่ตรวจสอบ/แก้ไข และจุดที่มนุษย์เป็นผู้ตัดสินใจ

## 1. ELT Pipeline (elt/)

**AI ทำ:** ออกแบบโครงสร้าง extract → load → transform → export → publish,
เขียน SQL ทั้งหมดใน `elt/sql/` (staging, dimensions, facts, quality checks),
เขียน SQL macro `clean_text()` สำหรับล้าง HTML ในข้อความรีวิว

**ตรวจสอบ/แก้ไข:**
- รัน pipeline จริงกับข้อมูลทั้งหมด (3.1 GB ดิบ) ไม่ใช่แค่ข้อมูลตัวอย่าง
- ทดสอบ `clean_text()` กับเคส edge case จริง (HTML ซ้อนกัน, entity escape สองชั้น
  เช่น `&amp;quot;`) ก่อนใช้งานจริง ยืนยันว่าไม่แปลงข้อความผิด
- Quality-check view 10 รายการทำงานจริง และหยุด export เมื่อพบปัญหา (ทดสอบ
  โดยตั้งใจใส่ข้อมูลเสียแล้วยืนยันว่า pipeline หยุดจริง)

**มนุษย์ตัดสินใจ:** เลือก 3 หมวดสินค้า (All_Beauty, Amazon_Fashion,
Health_and_Personal_Care), อนุมัติการดาวน์โหลดข้อมูลจริง 3.1 GB,
อนุมัติการ publish dataset ขึ้น Hugging Face และการเปิดเป็น public

## 2. Preprocessing Pipeline (preprocessing/)

**AI ทำ:** เขียน feature engineering, สร้าง label `sentiment`, ออกแบบการแบ่ง
train/val/test

**ตรวจสอบ/แก้ไข:** พบว่าปริมาณรีวิวปี 2022+ เก็บไม่ครบ (468K ปี 2021 → 58K ปี
2023) ทำให้การแบ่ง split เดิม (train<2022, val=2022, test=2023) ได้ test set
แค่ ~1.7% ของข้อมูล — แก้โดยเลื่อนเส้นแบ่งเป็นปี 2021/2022 (ได้สัดส่วน 77/14/10)
พร้อมเขียนคำเตือนถาวรลงใน dataset card และ dashboard

## 3. Analytics & Model (analytics/, model/)

**AI ทำ:** เขียน SQL ตอบคำถามกลุ่ม A ทั้ง 5 ข้อ, เขียนโมเดล scikit-learn ตอบ
คำถามกลุ่ม B ทั้ง 5 ข้อ (Regression, Classification, Clustering, Topic
Modeling, Anomaly Detection) พร้อมออกแบบ baseline สำหรับเทียบทุกโมเดล

**ตรวจสอบ/แก้ไข:**
- รันทุกโมเดลกับข้อมูลจริงทั้งหมด (ไม่ใช่ sample เล็ก ๆ) แล้วดูผลลัพธ์จริง
- **รายงานผลตามจริงแม้ไม่สวย** — โมเดล B1 (Regression) ไม่ชนะ baseline เลย
  (MAE: Baseline 0.4533 < Ridge 0.4543 < GradientBoosting 0.4744) รายงานผลนี้
  ตรงไปตรงมาในทุกที่ที่แสดงผล ไม่ปรับแต่งให้ดูดีกว่าความจริง
- เทียบตัวเลขสำคัญ (เช่น B2 macro-F1 = 0.704) กับ SQL ที่คำนวณแยกต่างหาก

**มนุษย์ตัดสินใจ:** สั่งให้ "รัน save model ไว้ก่อน" แทนการ retrain สดใน
dashboard — นำไปสู่การแพตช์โค้ดให้ `joblib.dump()` ทุกโมเดลหลังเทรน

## 4. Dashboard (dashboard/)

**AI ทำ:** เขียน Streamlit app ทั้งหมด (filter, KPI, 13 กราฟ Plotly, 4 แท็บ)

**ตรวจสอบ/แก้ไข — พบบั๊กจริง 2 จุดจากการทดสอบด้วย headless browser (Playwright)
ไม่ใช่แค่อ่านโค้ด:**

1. **Race condition ใน DuckDB connection** — `get_connection()` cache
   connection เดียวใช้ร่วมกันทุก query function ผ่าน `st.cache_resource`
   เมื่อมี rerun ซ้อนกัน (เช่นเปลี่ยน filter เร็ว ๆ) เกิด error
   `'NoneType' object has no attribute 'iloc'`
   - ทดสอบยืนยันสาเหตุด้วย concurrency stress test (15 เธรด เรียก query
     พร้อมกัน 15 ครั้งต่อเธรด): ใช้ connection ดิบร่วมกัน error 14/15 ครั้ง
   - แก้ด้วยการเปลี่ยนทุกฟังก์ชันให้ใช้ `connection.cursor()` แยกต่อคำสั่ง
     (วิธีที่ DuckDB แนะนำสำหรับใช้ connection เดียวพร้อมกันหลาย query)
   - ทดสอบซ้ำ (stress test เดิม): error เหลือ 0/15 ครั้ง

2. **สคริปต์จับภาพหน้าจอ scroll ไปผิด element** — ฟังก์ชัน `scrollToText`
   จับ `<div>` ที่ห่อทั้งหน้า (ซึ่ง textContent รวมทุกอย่างข้างในไว้ด้วย) แทนที่
   จะจับ heading จริง ทำให้ได้ภาพซ้ำ (B4/B5 มองไม่เห็น) — แก้โดยจำกัดการค้นหา
   เฉพาะ heading tag จริง (h1-h3) ก่อน แล้วค่อย fallback ไปหา element ที่มี
   ลูกหลานน้อยจริง ๆ

**มนุษย์ตัดสินใจ:** เลือกใช้ dataset ที่ผ่าน ELT pipeline (ไม่ใช่ dataset ที่
ผ่าน preprocessing) เป็นแหล่งข้อมูลสดของ dashboard

## 5. รายงาน (README.pdf)

**AI ทำ:** ร่างเนื้อหารายงานทั้งหมด, เขียน HTML/CSS ต้นแบบ, เขียนสคริปต์
Playwright จับภาพหน้าจอ dashboard, แปลง SVG diagram เป็น PNG, render เป็น PDF

**ตรวจสอบ/แก้ไข:**
- ตรวจทุกหน้า PDF ด้วยการ render เป็นรูปภาพจริง (pypdfium2) ไม่ใช่แค่เชื่อ
  ว่า CSS ที่เขียนจะได้ผลตามต้องการ
- พบว่าไฟล์แรกมี 19 หน้า (เกินเป้าหมาย 10-15 หน้า) เพราะมีหน้าที่เนื้อหาล้น
  ไปเป็นหน้าที่แทบว่างเปล่า — ไล่ตรวจทีละหน้าจนพบจุดล้นทั้งหมด (หน้า Star
  Schema, หน้าตัวอย่าง Dashboard ที่มี 3 รูปเรียงกัน, หน้า Insights) แก้จน
  เหลือ 15 หน้าพอดีเป้าหมาย ทุกหน้าใช้พื้นที่เต็ม

## 6. แปลงเป็น .docx

**AI ทำ:** แปลง HTML report เป็น .docx ผ่าน pandoc

**ตรวจสอบ/แก้ไข — พบปัญหาจริง 2 จุดจากการแปลงกลับเป็น PDF ดูซ้ำ:**
1. CSS `page-break-after` ที่ใช้ได้กับ PDF (Chromium) ใช้ไม่ได้กับ pandoc เลย
   — ทดสอบยืนยันด้วยการสร้างไฟล์ทดสอบเปล่า ๆ 3 แบบ (CSS legacy/ใหม่ทุกรูปแบบ)
   ยืนยันว่า pandoc ไม่แปลง page-break property ใด ๆ เป็น Word page break จริง
   — แก้ด้วยการแทรก text marker ในโค้ด HTML ก่อนแปลง แล้วใช้ python-docx
   แทนที่ marker ด้วย page break จริงหลังแปลงเสร็จ (14 จุด)
2. ชื่อเรื่องซ้ำ — pandoc ดึง `<title>` จาก HTML head มาสร้างหัวเรื่องเองซ้อน
   กับหัวเรื่องที่ออกแบบเองในเนื้อหา แก้โดยลบ tag `<title>` ออก

## สรุปหลักการตรวจสอบที่ยึดตลอดโปรเจกต์

1. รันจริงด้วยข้อมูลจริงทั้งหมดเสมอ ไม่เชื่อแค่ "โค้ดรันผ่านไม่ error"
2. ทดสอบผลลัพธ์ที่มองเห็นได้จริง (ภาพหน้าจอ, PDF render) แทนการอ่านโค้ดแล้ว
   สันนิษฐาน
3. เมื่อพบพฤติกรรมแปลก ให้เขียนการทดลองแยกเพื่อยืนยันสาเหตุก่อนแก้ (เช่น
   stress test ยืนยัน race condition, ไฟล์ทดสอบเปล่ายืนยันว่า pandoc ไม่รองรับ
   CSS page-break)
4. รายงานผลลัพธ์ตามจริงแม้ไม่สวย (เช่น โมเดล B1 ไม่ชนะ baseline)
5. การกระทำที่กระทบความเป็นส่วนตัว/ความปลอดภัย/สิ่งที่เผยแพร่ต่อสาธารณะ
   (เปิด dataset เป็น public, push ขึ้น git, deploy dashboard) ให้มนุษย์
   ยืนยันก่อนทุกครั้ง ไม่ตัดสินใจเองอัตโนมัติ
