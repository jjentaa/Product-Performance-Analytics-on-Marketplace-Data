"""E — Extract: ดาวน์โหลดไฟล์ JSONL ดิบจาก Hugging Face

ไฟล์จะลงที่ data/raw/ ตามโครงสร้างเดิมของ repo ต้นทาง
ดาวน์โหลดค้างไว้แล้วรันใหม่ได้ (resume) ถ้าไฟล์ครบแล้วจะข้าม
"""

from pathlib import Path

from huggingface_hub import hf_hub_download

from elt.common import ROOT, human_bytes, load_config

SOURCE_REPO = "McAuley-Lab/Amazon-Reviews-2023"
DATA_DIR = ROOT / "data"


def main() -> None:
    config = load_config()
    categories = config["categories"]
    print(f"[extract] domain: {config['domain']}")
    print(f"[extract] {len(categories)} categories: {', '.join(categories)}")

    total = 0
    for category in categories:
        for filename in (
            f"raw/review_categories/{category}.jsonl",
            f"raw/meta_categories/meta_{category}.jsonl",
        ):
            path = Path(
                hf_hub_download(
                    repo_id=SOURCE_REPO,
                    filename=filename,
                    repo_type="dataset",
                    local_dir=DATA_DIR,
                )
            )
            total += path.stat().st_size
            print(f"[extract]   {path.relative_to(ROOT)} ({human_bytes(path.stat().st_size)})")

    print(f"[extract] done — {human_bytes(total)} on disk")


if __name__ == "__main__":
    main()
