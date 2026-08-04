# Product Performance Analytics on Marketplace Data

Data pipeline 2 ขั้นสำหรับชุดข้อมูล [Amazon Reviews 2023](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023)
แปลงไฟล์ JSONL ดิบให้กลายเป็น dataset ที่พร้อมใช้บน Hugging Face

```
Hugging Face          ┌──────────── Stage 1: ELT ────────────┐   ┌─ Stage 2: Preprocessing ─┐
(JSONL ดิบ 3 หมวด)     extract → load → transform → export        โหลด → ล้าง → feature → split
       │                        (DuckDB, star schema)                    (DuckDB + notebook)
       └──────────────────────────────┬──────────────────────────────────────┬───────────────
                                      ▼                                      ▼
                          HF dataset #1: star schema          HF dataset #2: พร้อมเทรนโมเดล
```

**ทำไมต้องแยก 2 ขั้น** — dataset #1 เก็บโครงสร้างที่ใกล้เคียงต้นฉบับ (เหมาะกับคนที่อยาก
วิเคราะห์เอง/ทำ feature เอง) ส่วน dataset #2 คือชุดที่ตัดสินใจเรื่อง preprocessing ไปแล้ว
(เหมาะกับคนที่อยากเทรนโมเดลเลย) ถ้าใครไม่เห็นด้วยกับวิธี preprocess ก็ย้อนไปเริ่มจาก #1 ได้
โดยไม่ต้องรัน ELT ใหม่

## ขอบเขตข้อมูล

โฟกัส 3 หมวดที่รวมเป็นหมวดใหญ่เดียวกันได้ — **ความงามและการดูแลตัวเอง**
(Beauty & Personal Care) คือสินค้าที่คนซื้อมาใช้กับร่างกาย/รูปลักษณ์ตัวเอง
ทำให้เปรียบเทียบข้ามหมวดได้อย่างมีความหมาย และรวมกันแค่ ~3.4 GB

| หมวดย่อย | ขนาด (รีวิว + metadata) |
|---|---|
| `All_Beauty` | ~0.54 GB |
| `Health_and_Personal_Care` | ~0.35 GB |
| `Amazon_Fashion` | ~2.47 GB |

เปลี่ยนหมวดได้ที่ `categories` ใน [config.yaml](config.yaml)

## Stage 1 — ELT ([elt/](elt/))

| ขั้น | ไฟล์ | ทำอะไร |
|---|---|---|
| **E**xtract | [elt/extract.py](elt/extract.py) | ดาวน์โหลด JSONL จาก HF ลง `data/raw/` (resume ได้) |
| **L**oad | [elt/load.py](elt/load.py) | โหลดเข้า DuckDB schema `raw` ตามสภาพเดิม กำหนดแค่ type |
| **T**ransform | [elt/transform.py](elt/transform.py) + [elt/sql/](elt/sql/) | `raw` → `staging` → `marts` (star schema) |
| Export | [elt/export.py](elt/export.py) | เขียน Parquet + สร้าง dataset card จากตัวเลขจริง |
| Publish | [elt/publish.py](elt/publish.py) | อัพขึ้น Hugging Face |

**สิ่งที่ทำในขั้นนี้**

- ลบรีวิวซ้ำด้วย (`user_id`, `asin`, `timestamp`)
- กรองแถวเสีย: rating นอกช่วง 1–5, ไม่มี user/product/timestamp,
  timestamp เพี้ยนนอกช่วงปี 1996–2023
- แปลง `price` จาก string (`"None"`, `"14.99"`) เป็นตัวเลข แล้วจัดกลุ่มเป็น `price_band`
- สินค้าที่มีรีวิวแต่ไม่มี metadata ยังได้แถวใน `dim_product` (ธง `has_metadata = false`)
  → fact ไม่มีแถวกำพร้า
- quality checks 10 ข้อ ถ้าไม่ผ่านสักข้อ export จะไม่ยอมเขียนไฟล์ออก

**ยังไม่ทำ** — ล้าง HTML ในข้อความ, feature engineering, แบ่ง train/test (ยกไป stage 2
เพื่อให้ dataset #1 ใกล้เคียงต้นฉบับที่สุด)

### Star schema

Grain: **1 แถว = 1 รีวิว** — ดู diagram แบบแก้ไขได้ที่
[docs/star_schema.drawio](docs/star_schema.drawio) (เปิดด้วย [app.diagrams.net](https://app.diagrams.net)
หรือ extension draw.io ใน VS Code)

```
              dim_date
                 │
 dim_product ── fact_review ── dim_user
                 │
            review_text (ข้อความดิบ, join ด้วย review_id)
```

| ตาราง | Grain | คอลัมน์เด่น |
|---|---|---|
| `fact_review` | 1 รีวิว | `rating`, `helpful_vote`, `verified_purchase`, `has_images`, `is_positive/negative` |
| `dim_product` | 1 สินค้า (`parent_asin`) | `product_title`, `store` (แบรนด์), `price`, `price_band`, `has_metadata` |
| `dim_user` | 1 คนรีวิว | `lifetime_reviews`, `categories_reviewed`, `avg_rating_given`, `reviewer_segment` |
| `dim_date` | 1 วัน | `year`, `quarter`, `month`, `day_name`, `is_weekend` |
| `review_text` | 1 รีวิว | ข้อความ**ดิบ** แยกออกมาเพื่อให้ fact table เล็ก |

`dim_user` สร้างจากประวัติการรีวิว เพราะชุดข้อมูลต้นทางไม่มีโปรไฟล์ผู้ใช้แยกมาให้

## Stage 2 — Preprocessing ([preprocessing/preprocessing.ipynb](preprocessing/preprocessing.ipynb))

Notebook ที่โหลด star schema จาก HF (dataset #1) แล้วแปลงให้พร้อมเทรนโมเดล
ถ้ายังไม่ได้ push จะถอยไปอ่าน `data/elt_export/` ในเครื่องอัตโนมัติ — รันได้ตั้งแต่ก่อน push

**สิ่งที่ทำในขั้นนี้**

1. **ล้างข้อความ** — ลบ HTML tag (`<br />`, `<span>`) และ entity (`&#34;`, `&amp;`, `&nbsp;`)
   ยุบช่องว่างซ้ำ (`&amp;` ถอดรหัสท้ายสุด กัน `&amp;quot;` ที่ escape สองชั้นแปลงผิด)
2. **กรอง** — ตัดรีวิวที่เหลือน้อยกว่า 3 คำหลังล้าง
3. **สร้าง label** — `sentiment` (negative/neutral/positive) จาก rating
4. **feature ของข้อความ** — `word_count`, `char_count`, `avg_word_length`,
   `exclamation_count`, `question_count`, `uppercase_ratio`, `digit_count`
5. **รวม feature จาก dimension** — ราคา, แบรนด์, พฤติกรรมผู้รีวิว, สถิติของสินค้า
   (`product_avg_rating`, `rating_vs_product_avg`, `days_since_product_first_review`)
   → ปลายทางไม่ต้อง join เอง
6. **แบ่ง train/val/test ตามเวลา** ไม่ใช่สุ่ม เพื่อกัน data leakage
   (train < 2022, val = 2022, test ≥ 2023)
7. **ตรวจคุณภาพ** — ยืนยันว่าช่วงเวลาของแต่ละ split ไม่ทับกัน, ไม่มี null ในคอลัมน์บังคับ,
   `review_id` ไม่ซ้ำ แล้วรายงานความไม่สมดุลของคลาส

ผลลัพธ์: `reviews/` (แบ่ง partition ตาม `split`) และ `product_features.parquet`
(1 แถว = 1 สินค้า พร้อมสถิติสำหรับจัดอันดับ/หาสินค้าขาลง)

> ใช้ DuckDB เป็นตัวประมวลผลหลักแทน pandas เพราะข้อมูลหลายล้านแถวที่มีข้อความยาว
> ถ้าโหลดเข้า pandas ทั้งก้อนจะกิน RAM หนัก — DuckDB ทำงานบน Parquet ได้โดยตรงและ
> spill ลงดิสก์เองเมื่อหน่วยความจำไม่พอ ส่วน pandas ใช้ดูผลลัพธ์ระหว่างทาง

## วิธีรัน

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**Stage 1:**

```bash
python -m elt.run_elt
```

รัน extract → load → transform → export ครบ (ครั้งแรกดาวน์โหลด ~3.4 GB)
รันทีละขั้นก็ได้: `python -m elt.extract`, `python -m elt.load`,
`python -m elt.transform`, `python -m elt.export`

จากนั้นแก้ `elt.repo_id` ใน [config.yaml](config.yaml) เป็น `<hf-username>/<dataset-name>` แล้ว push:

```bash
huggingface-cli login
python -m elt.publish --dry-run
python -m elt.publish
```

**Stage 2:** เปิด [preprocessing/preprocessing.ipynb](preprocessing/preprocessing.ipynb)
ใน Jupyter/VS Code แล้ว Run All — cell สุดท้ายตั้ง `dry_run=True` ไว้
เปลี่ยนเป็น `False` เมื่อพร้อม push จริง

> repo ทั้งสองชุดสร้างเป็น **private** ก่อนเสมอ ค่อยไปกดเปิด public บนเว็บ HF ทีหลัง
> เมื่อตรวจแล้วพอใจ

### พื้นที่ดิสก์

| อะไร | ประมาณ |
|---|---|
| `data/raw/` (JSONL ดิบ) | ~3.4 GB |
| `data/warehouse/` (DuckDB) | ~4–6 GB |
| `data/elt_export/` + `data/preprocessed/` (Parquet) | ~2 GB |

รวม ~10 GB — ถ้า RAM น้อยให้ลด `elt.memory_limit` ใน config
DuckDB จะ spill ลงดิสก์เองแทนที่จะ crash

## เพื่อนเอาไปใช้ต่อยังไง

```python
import pandas as pd

# ชุดพร้อมเทรน (dataset #2)
train = pd.read_parquet("hf://datasets/<username>/amazon-beauty-analytics-ready/reviews",
                        filters=[("split", "=", "train")])
X, y = train["text_full"], train["sentiment"]

# ชุด star schema (dataset #1) — อยากทำ feature เอง
fact = pd.read_parquet("hf://datasets/<username>/amazon-beauty-star-schema/fact_review",
                       filters=[("category", "=", "All_Beauty")])
```

## คำถามธุรกิจ

รายละเอียดเต็มพร้อม SQL ที่รันได้จริงและวิธีตั้งโจทย์โมเดล:
**[docs/business_questions.md](docs/business_questions.md)**

**กลุ่ม A — ตอบได้จากการ analyze** (SQL/pandas ไม่ต้องสร้างโมเดล)

| # | คำถาม | ได้อะไร |
|---|-------|--------|
| A1 | แบรนด์ไหนแข็งที่สุดในแต่ละหมวดย่อย | ตาราง benchmark |
| A2 | ราคาแพงขึ้นแล้วลูกค้าพอใจขึ้นจริงไหม | จุดที่ตั้งราคาเกินคุณค่า |
| A3 | สินค้าไหนกำลังขาลง (คะแนนช่วงหลังตก) | รายชื่อสินค้าต้องเฝ้าระวัง |
| A4 | รีวิวแบบไหนที่คนบอกว่ามีประโยชน์ | เกณฑ์จัดลำดับรีวิว |
| A5 | 3 หมวดต่างกันแค่ไหน คะแนนใครน่าเชื่อถือน้อยสุด | เงื่อนไขการเทียบข้ามหมวด |

**กลุ่ม B — ต้องสร้างโมเดล** (ใช้ dataset #2 เป็น feature/label ได้เลย)

| # | คำถาม | โมเดล |
|---|-------|-------|
| B1 | สินค้าใหม่จะได้คะแนนเท่าไหร่ | Regression |
| B2 | ข้อความในรีวิวตรงกับดาวที่ให้ไหม | Classification (NLP) |
| B3 | สินค้าแบ่งได้เป็นกี่กลุ่มตาม performance | Clustering |
| B4 | ลูกค้าบ่นเรื่องอะไรในรีวิวเชิงลบ | Topic modeling |
| B5 | รีวิวไหนน่าสงสัยว่าปลอม/จ้าง | Anomaly detection |

หลักแบ่งง่าย ๆ: ถ้า `GROUP BY` ตอบได้ = กลุ่ม A ส่วนคำถามที่ต้อง**อ่านข้อความอิสระ**,
**ทำนายอนาคต** หรือ**หาโครงสร้างที่ซ่อนอยู่** = กลุ่ม B

## ข้อควรระวัง

- รีวิวเดียวอาจปรากฏในไฟล์หมวดมากกว่าหนึ่งไฟล์ การ dedupe ยุบเหลือแถวเดียว
  จำนวนรายหมวดจึงต่ำกว่าจำนวนบรรทัดในไฟล์ดิบเล็กน้อย
- `dim_user` คำนวณจาก 3 หมวดนี้เท่านั้น ไม่ใช่ประวัติ Amazon ทั้งหมดของคนนั้น
- จำนวนรีวิวเป็นตัวแทนคร่าว ๆ ของดีมานด์ **ไม่ใช่ยอดขาย** — ต้นทางไม่มีข้อมูลยอดขาย
- คลาสไม่สมดุล รีวิว 4–5 ดาวเยอะกว่ามาก ตอนเทรนควรใช้ `class_weight` หรือ resampling
- `product_avg_rating` คำนวณจากทั้งชุด ถ้าซีเรียสเรื่อง leakage ให้คำนวณใหม่จากเฉพาะ train

## โครงสร้างโปรเจกต์

```
config.yaml                      ตั้งค่ากลาง: หมวด, DuckDB, export, repo_id ทั้งสอง stage
elt/
  common.py                      โหลด config, เปิด DuckDB, ฟังก์ชัน push ขึ้น HF
  extract.py                     ดาวน์โหลด JSONL จาก Hugging Face
  load.py                        โหลดเข้า DuckDB schema raw
  transform.py                   รัน SQL ตามลำดับ + quality checks
  sql/10_staging.sql             raw -> staging (type, dedupe, กรองแถวเสีย)
  sql/20_dimensions.sql          dim_date, dim_product, dim_user
  sql/30_facts.sql               fact_review + review_text
  sql/40_quality_checks.sql      view ตรวจคุณภาพ + สรุปรายหมวด
  export.py                      marts -> Parquet + dataset card
  dataset_card.py                template dataset card ของทั้งสอง stage
  publish.py                     push dataset #1 ขึ้น HF
  run_elt.py                     รัน stage 1 ครบทุกขั้น
preprocessing/
  preprocessing.ipynb            stage 2 ทั้งหมด: โหลด → ล้าง → feature → split → push
docs/
  business_questions.md          คำถามธุรกิจ 10 ข้อ + SQL + วิธีตั้งโจทย์โมเดล
  star_schema.drawio             ER diagram แบบแก้ไขได้
data/                            ไฟล์ดิบ + warehouse + export (gitignore ไว้)
```
