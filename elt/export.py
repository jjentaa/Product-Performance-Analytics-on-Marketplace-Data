"""Export: เขียน star schema ออกเป็น Parquet + สร้าง dataset card

โครงสร้างที่ได้ใต้ data/elt_export/ (โฟลเดอร์นี้คือสิ่งที่ push ขึ้น HF):

    fact_review/category=<name>/*.parquet    1 แถว = 1 รีวิว (ไม่มีข้อความ)
    review_text/category=<name>/*.parquet    ข้อความรีวิวดิบ
    dim_product.parquet
    dim_user.parquet
    dim_date.parquet
    stats.json
    README.md                                dataset card

แบ่ง partition ด้วย category เพื่อให้ปลายทางอ่านทีละหมวดได้โดยไม่ต้องสแกนทั้งไฟล์
"""

import json
import shutil
from pathlib import Path

from elt.common import ROOT, connect, folder_size, human_bytes, load_config
from elt.dataset_card import render_elt_card

PARTITIONED = ["fact_review", "review_text"]
FLAT = ["dim_product", "dim_user", "dim_date"]


def main() -> None:
    config = load_config()
    export_dir = ROOT / config["elt"]["export_path"]
    if export_dir.exists():
        shutil.rmtree(export_dir)
    export_dir.mkdir(parents=True)

    con = connect(config)

    failures = con.execute(
        "SELECT check_name, bad_rows FROM marts.v_quality_checks WHERE status = 'FAIL'"
    ).fetchall()
    if failures:
        details = "\n".join(f"  - {name}: {n:,} rows" for name, n in failures)
        raise RuntimeError(f"quality checks ไม่ผ่าน ไม่ export:\n{details}")
    print("[export] quality checks: all PASS")

    for table in PARTITIONED:
        target = export_dir / table
        con.execute(f"""
            COPY (SELECT * FROM marts.{table}) TO '{target}'
            (FORMAT PARQUET, PARTITION_BY (category),
             COMPRESSION ZSTD, OVERWRITE_OR_IGNORE)
        """)
        print(f"[export] {table:<12} -> {table}/category=*/  ({human_bytes(folder_size(target))})")

    for table in FLAT:
        target = export_dir / f"{table}.parquet"
        con.execute(f"COPY marts.{table} TO '{target}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        print(f"[export] {table:<12} -> {table}.parquet  ({human_bytes(target.stat().st_size)})")

    summary = con.execute("SELECT * FROM marts.v_category_summary")
    cols = [c[0] for c in summary.description]
    per_category = [dict(zip(cols, row)) for row in summary.fetchall()]
    for row in per_category:
        row["first_review"] = str(row["first_review"])
        row["last_review"] = str(row["last_review"])

    stats = {
        "stage": "elt",
        "source_dataset": "McAuley-Lab/Amazon-Reviews-2023",
        "domain": config["domain"],
        "categories": config["categories"],
        "row_counts": {
            table: con.execute(f"SELECT count(*) FROM marts.{table}").fetchone()[0]
            for table in PARTITIONED + FLAT
        },
        "per_category": per_category,
    }
    (export_dir / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False))
    (export_dir / "README.md").write_text(render_elt_card(config, stats))
    con.close()

    print(f"[export] stats.json + README.md (dataset card) เขียนแล้ว")
    print(f"[export] total: {human_bytes(folder_size(export_dir))} -> {export_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
