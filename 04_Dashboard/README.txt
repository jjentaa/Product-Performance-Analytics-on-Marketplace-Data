04_Dashboard — Streamlit Interactive Dashboard
=================================================

Live URL: [รอ URL หลัง deploy บน Streamlit Community Cloud — อัปเดตก่อนส่งจริง]

โฟลเดอร์นี้คือสำเนาโค้ด dashboard (path เดิม: dashboard/) รันจาก root ของ
repository หลักเท่านั้น (ต้องมี elt/common.py และ config.yaml อยู่ระดับบนสุด
ของ repo ให้ import ได้)

ไฟล์
-----
app.py            หน้าหลัก Streamlit — 3 filter, 4 KPI, 4 แท็บ (Analytics,
                  Model Insights, Insights & ข้อเสนอแนะ, ข้อจำกัดของข้อมูล)
charts.py         ตัวสร้างกราฟ Plotly ทั้งหมด (13 กราฟ)
data_loader.py    query สดผ่าน DuckDB บน dataset #1 (star schema) +
                  โหลดผลลัพธ์โมเดลที่เทรนไว้แล้ว
data/model_artifacts/   โมเดลที่เทรนแล้ว (.joblib) สำหรับคำถาม B1-B5
data/model_output/      ตารางผลลัพธ์จากโมเดล (CSV/Parquet) ที่ dashboard
                        เอาไปแสดงผล — ไม่ retrain สดในแอป

วิธีรัน (จาก root ของ repository หลัก)
------------------------------------------
  pip install -r requirements.txt
  streamlit run dashboard/app.py

ภาพหน้าจอครบทุกแท็บ + ตัวอย่างการใช้ filter: ดู README.pdf หัวข้อ 8
