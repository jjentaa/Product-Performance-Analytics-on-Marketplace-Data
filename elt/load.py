"""L — Load: โหลด JSONL ดิบเข้า DuckDB schema `raw` ตามสภาพเดิม

ตามหลัก ELT: ขั้นนี้ไม่ clean อะไรทั้งนั้น แค่กำหนด type ให้ชัดเจน
เพื่อให้ชั้น transform มี contract ที่แน่นอนไว้ทำงานต่อ
โหลดทีละหมวดเพื่อคุมการใช้หน่วยความจำ
"""

import time

from elt.common import ROOT, connect, human_bytes, load_config

REVIEW_COLUMNS = {
    "rating": "DOUBLE",
    "title": "VARCHAR",
    "text": "VARCHAR",
    "images": "JSON",
    "asin": "VARCHAR",
    "parent_asin": "VARCHAR",
    "user_id": "VARCHAR",
    "timestamp": "BIGINT",
    "helpful_vote": "BIGINT",
    "verified_purchase": "BOOLEAN",
}

# price มาเป็น string ("None", "14.99") — cast ทีหลังในชั้น staging
META_COLUMNS = {
    "main_category": "VARCHAR",
    "title": "VARCHAR",
    "average_rating": "DOUBLE",
    "rating_number": "BIGINT",
    "features": "JSON",
    "description": "JSON",
    "price": "VARCHAR",
    "images": "JSON",
    "videos": "JSON",
    "store": "VARCHAR",
    "categories": "JSON",
    "details": "JSON",
    "parent_asin": "VARCHAR",
    "bought_together": "JSON",
}


def columns_sql(columns: dict[str, str]) -> str:
    return "{" + ", ".join(f"'{k}': '{v}'" for k, v in columns.items()) + "}"


def main() -> None:
    config = load_config()
    con = connect(config)
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")

    review_cols = ", ".join(f'"{k}" {v}' for k, v in REVIEW_COLUMNS.items())
    meta_cols = ", ".join(f'"{k}" {v}' for k, v in META_COLUMNS.items())
    con.execute(f"CREATE OR REPLACE TABLE raw.reviews ({review_cols}, source_category VARCHAR)")
    con.execute(f"CREATE OR REPLACE TABLE raw.meta ({meta_cols}, source_category VARCHAR)")

    for category in config["categories"]:
        targets = [
            ("raw.reviews",
             ROOT / "data" / "raw" / "review_categories" / f"{category}.jsonl",
             REVIEW_COLUMNS),
            ("raw.meta",
             ROOT / "data" / "raw" / "meta_categories" / f"meta_{category}.jsonl",
             META_COLUMNS),
        ]
        for _, path, _ in targets:
            if not path.exists():
                raise FileNotFoundError(f"ไม่พบ {path} — รัน `python -m elt.extract` ก่อน")

        for table, path, columns in targets:
            started = time.perf_counter()
            con.execute(
                f"""
                INSERT INTO {table}
                SELECT *, ? AS source_category
                FROM read_json(?, format='newline_delimited',
                               columns={columns_sql(columns)})
                """,
                [category, str(path)],
            )
            rows = con.execute(
                f"SELECT count(*) FROM {table} WHERE source_category = ?", [category]
            ).fetchone()[0]
            print(
                f"[load] {table:<12} <- {category:<26} {rows:>12,} rows  "
                f"({human_bytes(path.stat().st_size)}, {time.perf_counter() - started:.0f}s)"
            )

    con.close()
    print(f"[load] done -> {config['elt']['duckdb_path']}")


if __name__ == "__main__":
    main()
