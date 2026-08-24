"""Publish: อัพ data/elt_export/ ขึ้น Hugging Face

ขั้นนี้เป็นขั้นเดียวที่ติดต่อโลกภายนอก จึงไม่รวมอยู่ใน run_elt.py — ต้องสั่งเอง

    huggingface-cli login        # ครั้งเดียว
    python -m elt.publish --dry-run
    python -m elt.publish
"""

import argparse
import sys

from elt.common import ROOT, load_config, push_folder


def main() -> None:
    parser = argparse.ArgumentParser(description="อัพ ELT dataset ขึ้น Hugging Face")
    parser.add_argument("--dry-run", action="store_true",
                        help="แสดงว่าจะอัพอะไรบ้าง แล้วออก")
    args = parser.parse_args()

    config = load_config()
    settings = config["elt"]
    try:
        push_folder(
            folder=ROOT / settings["export_path"],
            repo_id=settings["repo_id"],
            private=settings["private"],
            message=f"ELT star schema — {config['domain']} ({len(config['categories'])} categories)",
            dry_run=args.dry_run,
        )
    except (FileNotFoundError, ValueError) as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
