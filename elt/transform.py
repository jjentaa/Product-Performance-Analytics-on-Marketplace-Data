"""T — Transform: raw -> staging -> star schema

รันไฟล์ SQL ใน elt/sql/ ตามลำดับ แล้วสรุปผลให้ดู
"""

from pathlib import Path

from elt.common import connect, load_config

SQL_DIR = Path(__file__).resolve().parent / "sql"
MART_TABLES = (
    "fact_review", "review_text", "dim_product", "dim_user", "dim_date",
    "dim_brand", "dim_category", "dim_reviewer_segment",
)


def main() -> None:
    config = load_config()
    con = connect(config)

    for sql_file in sorted(SQL_DIR.glob("*.sql")):
        print(f"[transform] {sql_file.name} ...")
        con.execute(sql_file.read_text())

    print("[transform] row counts:")
    for table in MART_TABLES:
        n = con.execute(f"SELECT count(*) FROM marts.{table}").fetchone()[0]
        print(f"[transform]   marts.{table:<13} {n:>12,}")

    checks = con.execute(
        "SELECT check_name, bad_rows FROM marts.v_quality_checks WHERE status = 'FAIL'"
    ).fetchall()
    if checks:
        details = "\n".join(f"  - {name}: {n:,} rows" for name, n in checks)
        raise RuntimeError(f"[transform] quality checks FAILED:\n{details}")
    print("[transform] quality checks: all PASS")

    con.close()


if __name__ == "__main__":
    main()
