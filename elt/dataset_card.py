"""สร้าง dataset card (README.md) ของ HF จากตัวเลขจริงหลัง export

มีสองใบ: ใบของ ELT stage (star schema) และใบของ preprocessing stage (ML-ready)
"""

ELT_CARD = """---
license: mit
language:
  - en
tags:
  - amazon
  - reviews
  - star-schema
  - data-warehouse
  - ecommerce
size_categories:
  - {size_category}
---

# Amazon Reviews 2023 — {domain} (Star Schema)

**Stage 1 of 2.** โครงสร้าง star schema ที่ทำจาก
[McAuley-Lab/Amazon-Reviews-2023](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023)
เฉพาะหมวดใหญ่ **{domain}** ({n_categories} หมวดย่อย)

ขั้นนี้ทำแค่ **จัดโครงสร้าง** — ยังไม่ทำความสะอาดข้อความ ไม่ทำ feature engineering
ถ้าต้องการชุดที่พร้อมเทรนโมเดล ดู stage 2: [`{next_repo}`](https://huggingface.co/datasets/{next_repo})

## ไฟล์ในชุดนี้

| ไฟล์ | จำนวนแถว | Grain |
|------|---------|-------|
| `fact_review/` | {fact_review:,} | 1 แถว = 1 รีวิว (ไม่มีข้อความ) |
| `review_text/` | {review_text:,} | ข้อความรีวิว **ดิบ** (ยังมี HTML ปน) |
| `dim_product.parquet` | {dim_product:,} | 1 แถว = 1 สินค้า (`parent_asin`) |
| `dim_user.parquet` | {dim_user:,} | 1 แถว = 1 คนรีวิว |
| `dim_date.parquet` | {dim_date:,} | 1 แถว = 1 วัน |

`fact_review/` และ `review_text/` แบ่ง partition ตามหมวด (`category=<name>/`)
อ่านทีละหมวดได้โดยไม่ต้องสแกนทั้งชุด

## หมวดย่อย

{category_table}

## เริ่มใช้งาน

```python
import pandas as pd

fact = pd.read_parquet("hf://datasets/{repo_id}/fact_review")
products = pd.read_parquet("hf://datasets/{repo_id}/dim_product.parquet")

fact.merge(products, on="product_key").groupby("price_band")["rating"].mean()
```

อ่านเฉพาะหมวดเดียว:

```python
pd.read_parquet("hf://datasets/{repo_id}/fact_review",
                filters=[("category", "=", "All_Beauty")])
```

## Schema

`fact_review` — grain: 1 รีวิว

| คอลัมน์ | ชนิด | หมายเหตุ |
|--------|------|---------|
| `review_id` | string | md5 ของ (user_id, asin, timestamp) |
| `date_key` | int32 | → `dim_date`, รูปแบบ YYYYMMDD |
| `product_key` | int64 | → `dim_product` |
| `user_key` | int64 | → `dim_user` |
| `category` | string | partition key |
| `rating` | double | 1–5 |
| `helpful_vote` | int64 | จำนวนคนกดว่ามีประโยชน์ |
| `verified_purchase` | bool | ซื้อจริงหรือไม่ |
| `has_images` | bool | ผู้รีวิวแนบรูปไหม |
| `is_positive` / `is_negative` | bool | rating ≥ 4 / ≤ 2 |
| `review_ts` | timestamp | |

`dim_product` มี `product_title`, `main_category`, `store` (แบรนด์), `price`,
`price_band`, `listed_avg_rating`, `listed_rating_count`, `has_metadata`

`dim_user` มี `lifetime_reviews`, `categories_reviewed`, `avg_rating_given`,
`verified_share`, `first`/`last_review_date`, `reviewer_segment`
(Power reviewer / Regular / One-off)

## สิ่งที่ทำในขั้นนี้

- ลบรีวิวซ้ำด้วย (`user_id`, `asin`, `timestamp`)
- กรองแถวเสีย: rating นอกช่วง 1–5, ไม่มี user/product/timestamp,
  timestamp เพี้ยนนอกช่วงปี 1996–2023
- แปลง `price` จาก string เป็นตัวเลข แล้วจัดกลุ่มเป็น `price_band`
- สินค้าที่มีรีวิวแต่ไม่มี metadata ยังได้แถวใน `dim_product`
  (ธง `has_metadata = false`) — fact จึงไม่มีแถวกำพร้า
- ผ่าน quality checks 10 ข้อ (referential integrity, ค่าซ้ำ, ค่านอกช่วง)

**ยังไม่ได้ทำ:** ล้าง HTML ในข้อความ, feature engineering, แบ่ง train/test —
อยู่ใน stage 2

## ความครบถ้วนของ metadata (อ่านก่อนใช้ `price`)

ตัวเลขถ่วงน้ำหนัก**ตามจำนวนรีวิว** คือสัดส่วนที่จะเหลือจริงเมื่อคุณ join กับ `dim_product`

{coverage_table}

⚠️ **ข้อมูลราคาที่ขาดหายไม่ได้สุ่ม (MNAR)** — สินค้าที่ไม่มีราคาใน metadata
ได้คะแนนเฉลี่ยต่างจากสินค้าที่มีราคาอย่างเห็นได้ชัด:

{price_bias_table}

แปลว่าถ้าคุณกรอง `price_band = 'Unknown'` ทิ้งเพื่อวิเคราะห์เรื่องราคา
**ผลลัพธ์จะเอนไปทางบวก** ไม่ใช่แค่ "ตัวอย่างเล็กลง" ควรรายงานทุกครั้งว่ากรองออกไปกี่ %
และอย่าเอาข้อสรุปจาก subset นี้ไปอ้างกับสินค้าทั้งหมด

## ข้อควรระวัง

- รีวิวเดียวอาจปรากฏในไฟล์หมวดมากกว่าหนึ่งไฟล์ การ dedupe ยุบเหลือแถวเดียว
  จำนวนรายหมวดจึงต่ำกว่าจำนวนบรรทัดในไฟล์ดิบเล็กน้อย
- `dim_user` คำนวณจาก {n_categories} หมวดนี้เท่านั้น ไม่ใช่ประวัติ Amazon ทั้งหมดของคนนั้น
- จำนวนรีวิวเป็นตัวแทนคร่าว ๆ ของดีมานด์ ไม่ใช่ยอดขาย — ต้นทางไม่มีข้อมูลยอดขาย

## ที่มาและสัญญาอนุญาต

ดัดแปลงจาก [McAuley-Lab/Amazon-Reviews-2023](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023)
(UCSD McAuley Lab) กรุณาอ้างอิงผู้จัดทำต้นฉบับ:

```bibtex
@article{{hou2024bridging,
  title={{Bridging Language and Items for Retrieval and Recommendation}},
  author={{Hou, Yupeng and Li, Jiacheng and He, Zhankui and Yan, An and Chen, Xiusi and McAuley, Julian}},
  journal={{arXiv preprint arXiv:2403.03952}},
  year={{2024}}
}}
```
"""


PREP_CARD = """---
license: mit
task_categories:
  - text-classification
  - tabular-classification
language:
  - en
tags:
  - amazon
  - reviews
  - nlp
  - sentiment-analysis
  - feature-engineering
size_categories:
  - {size_category}
---

# Amazon Reviews 2023 — {domain} (Analytics / ML Ready)

**Stage 2 of 2.** ต่อยอดจาก star schema ใน
[`{elt_repo}`](https://huggingface.co/datasets/{elt_repo})
โดยทำความสะอาดข้อความ สร้าง feature และแบ่ง train/val/test ตามเวลาให้เรียบร้อย
โหลดแล้วเทรนโมเดลได้เลย

## ไฟล์ในชุดนี้

| ไฟล์ | จำนวนแถว | ใช้ทำอะไร |
|------|---------|----------|
| `reviews/split=train/` | {train:,} | เทรนโมเดล |
| `reviews/split=val/` | {val:,} | จูน hyperparameter |
| `reviews/split=test/` | {test:,} | วัดผลครั้งสุดท้าย |
| `product_features.parquet` | {product_features:,} | feature ระดับสินค้า |

แบ่ง partition ด้วย `split` — โหลดเฉพาะชุดที่ต้องการได้

## การแบ่ง train/val/test

แบ่ง**ตามเวลา** ไม่ใช่สุ่ม เพื่อไม่ให้โมเดลเห็นอนาคต (data leakage):

| Split | ช่วงเวลา | จำนวน |
|-------|---------|-------|
| train | ก่อน {val_start} | {train:,} |
| val | {val_start} ถึง {test_start} | {val:,} |
| test | ตั้งแต่ {test_start} | {test:,} |

## คอลัมน์

**ข้อความ**

| คอลัมน์ | หมายเหตุ |
|--------|---------|
| `review_text_clean` | ล้าง HTML tag/entity + ยุบช่องว่างแล้ว |
| `review_title_clean` | หัวข้อที่ล้างแล้ว |
| `text_full` | หัวข้อ + เนื้อหา รวมกัน (ใช้ป้อนโมเดลได้เลย) |

**Label**

| คอลัมน์ | หมายเหตุ |
|--------|---------|
| `sentiment` | `negative` (1–2 ดาว) / `neutral` (3) / `positive` (4–5) |
| `is_negative` | bool — ใช้ทำ binary classification |
| `rating` | 1–5 — ใช้ทำ regression / ordinal |

**Feature ของข้อความ**

`word_count`, `char_count`, `avg_word_length`, `exclamation_count`,
`question_count`, `uppercase_ratio`, `digit_count`

**Feature ของบริบท** (join มาจาก dimension แล้ว ไม่ต้อง join เอง)

`price`, `price_band`, `store`, `verified_purchase`, `has_images`,
`helpful_vote`, `user_lifetime_reviews`, `user_avg_rating_given`,
`reviewer_segment`, `product_review_count`, `product_avg_rating`,
`rating_vs_product_avg`, `review_year`, `review_month`, `days_since_product_first_review`

## เริ่มใช้งาน

```python
import pandas as pd

train = pd.read_parquet("hf://datasets/{repo_id}/reviews",
                        filters=[("split", "=", "train")])
test = pd.read_parquet("hf://datasets/{repo_id}/reviews",
                       filters=[("split", "=", "test")])

X_train, y_train = train["text_full"], train["sentiment"]
```

## สิ่งที่ทำในขั้นนี้

1. **ล้างข้อความ** — ลบ HTML tag (`<br />`, `<span>`) และ entity
   (`&#34;`, `&amp;`, `&nbsp;`) ยุบช่องว่างซ้ำ
2. **กรอง** — ตัดรีวิวที่เหลือน้อยกว่า {min_words} คำหลังล้าง
3. **สร้าง label** — `sentiment` จาก rating
4. **สร้าง feature ของข้อความ** — ความยาว, จำนวน `!`, สัดส่วนตัวพิมพ์ใหญ่ ฯลฯ
5. **รวม feature จาก dimension** — ราคา, แบรนด์, พฤติกรรมผู้รีวิว, สถิติของสินค้า
6. **แบ่ง train/val/test ตามเวลา**

## ⚠️ ปริมาณรีวิวช่วงท้ายไม่สมบูรณ์ — ห้ามตีความเป็นแนวโน้มดีมานด์

จำนวนรีวิวต่อปีในชุดนี้ร่วงลงอย่างมากในปีท้าย ๆ:

{yearly_table}

การร่วงนี้แทบแน่นอนว่าเป็น**ข้อจำกัดของการเก็บข้อมูลต้นทาง** (ชุดข้อมูลถูกเก็บกลางปี 2023
รีวิวใหม่ยังไม่ถูกรวบรวมครบ) **ไม่ใช่ยอดขายหรือความสนใจของลูกค้าที่ลดลงจริง**

ผลที่ตามมา:

- **ห้าม**สรุปว่า "ดีมานด์หมวดนี้หดตัว" จากกราฟจำนวนรีวิวรายปี
- ถ้าจะวิเคราะห์แนวโน้มตามเวลา ให้ตัดข้อมูลปี 2022 เป็นต้นไปออก หรือใช้
  **ค่าเฉลี่ยคะแนน** (ซึ่งไม่ขึ้นกับจำนวน) แทน**จำนวนรีวิว**
- การแบ่ง split จึงเลื่อนเส้นมาหนึ่งปี (val = 2021, test = 2022 เป็นต้นไป)
  ไม่งั้น test จะเหลือแค่ ~1.7% ของข้อมูล

## ข้อควรระวัง

- คลาสไม่สมดุล — รีวิว 4–5 ดาวเยอะกว่ามาก ตอนเทรนควรใช้ `class_weight`
  หรือทำ resampling
- **สัดส่วนคลาสเปลี่ยนตามเวลา** — สัดส่วนรีวิวเชิงลบใน val/test สูงกว่า train
  อย่าตกใจถ้าคะแนนบน test ต่ำกว่าที่คาด นั่นคือ distribution shift จริงในข้อมูล
- `product_avg_rating` และ `product_review_count` คำนวณจาก**ทั้งชุด**
  ถ้าซีเรียสเรื่อง leakage ให้คำนวณใหม่จากเฉพาะ train
- ข้อความเป็นภาษาอังกฤษเป็นหลัก แต่ไม่ได้กรองภาษาออก

## ที่มา

ดัดแปลงจาก [McAuley-Lab/Amazon-Reviews-2023](https://huggingface.co/datasets/McAuley-Lab/Amazon-Reviews-2023)
(UCSD McAuley Lab) ผ่าน [`{elt_repo}`](https://huggingface.co/datasets/{elt_repo})
"""


def size_category(n_rows: int) -> str:
    for limit, label in (
        (1_000, "n<1K"), (10_000, "1K<n<10K"), (100_000, "10K<n<100K"),
        (1_000_000, "100K<n<1M"), (10_000_000, "1M<n<10M"),
        (100_000_000, "10M<n<100M"),
    ):
        if n_rows < limit:
            return label
    return "100M<n<1B"


def render_elt_card(config: dict, stats: dict) -> str:
    counts = stats["row_counts"]
    header = "| หมวด | รีวิว | สินค้า | ผู้รีวิว | คะแนนเฉลี่ย | ซื้อจริง | ช่วงเวลา |"
    divider = "|---|---|---|---|---|---|---|"
    rows = [
        f"| `{r['category']}` | {r['n_reviews']:,} | {r['n_products']:,} | "
        f"{r['n_users']:,} | {r['avg_rating']} | {r['verified_share']:.0%} | "
        f"{r['first_review']} → {r['last_review']} |"
        for r in stats["per_category"]
    ]
    cov_rows = [
        f"| `{r['category']}` | {r.get('price_coverage', 0):.1%} | {r.get('brand_coverage', 0):.1%} |"
        for r in stats["per_category"]
    ]
    coverage_table = "\n".join([
        "| หมวด | รู้ราคา | รู้แบรนด์ |", "|---|---|---|", *cov_rows,
    ])

    bias_rows = [
        f"| {'มีราคาใน metadata' if r['has_price'] else 'ไม่มีราคา'} | "
        f"{r['n_reviews']:,} | {r['avg_rating']} |"
        for r in stats.get("price_missingness", [])
    ]
    price_bias_table = "\n".join([
        "| กลุ่ม | จำนวนรีวิว | คะแนนเฉลี่ย |", "|---|---|---|", *bias_rows,
    ])

    return ELT_CARD.format(
        size_category=size_category(counts["fact_review"]),
        domain=config["domain"],
        n_categories=len(config["categories"]),
        category_table="\n".join([header, divider, *rows]),
        coverage_table=coverage_table,
        price_bias_table=price_bias_table,
        repo_id=config["elt"]["repo_id"],
        next_repo=config["preprocessing"]["repo_id"],
        **counts,
    )


def render_prep_card(config: dict, stats: dict) -> str:
    counts = stats["split_counts"]

    yearly = stats.get("yearly_volume", [])
    peak = max((n for _, n in yearly), default=0)
    yearly_table = "\n".join([
        "| ปี | จำนวนรีวิว | เทียบปีที่สูงสุด |", "|---|---|---|",
        *[f"| {y} | {n:,} | {n / peak:.0%} |" for y, n in yearly],
    ])

    return PREP_CARD.format(
        yearly_table=yearly_table,
        size_category=size_category(sum(counts.values())),
        domain=config["domain"],
        repo_id=config["preprocessing"]["repo_id"],
        elt_repo=config["elt"]["repo_id"],
        min_words=config["preprocessing"]["min_words"],
        val_start=config["preprocessing"]["val_start"],
        test_start=config["preprocessing"]["test_start"],
        product_features=stats["product_features"],
        **counts,
    )
