"""Shared helpers: config loading, DuckDB connections, formatting."""

from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    with open(ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def connect(config: dict | None = None) -> duckdb.DuckDBPyConnection:
    """Open the warehouse with the resource limits from config.yaml."""
    config = config or load_config()
    settings = config["elt"]
    db_path = ROOT / settings["duckdb_path"]
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path))
    con.execute(f"SET memory_limit = '{settings['memory_limit']}'")
    con.execute(f"SET threads = {int(settings['threads'])}")
    # spill next to the database rather than into /tmp
    con.execute(f"SET temp_directory = '{db_path.parent / 'duckdb_tmp'}'")
    return con


def human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def folder_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def push_folder(folder: Path, repo_id: str, private: bool, message: str,
                dry_run: bool = False) -> str:
    """อัพโฟลเดอร์ขึ้น Hugging Face เป็น dataset repo (ใช้ร่วมกันทั้งสอง stage)."""
    from huggingface_hub import HfApi

    folder = Path(folder)
    if not folder.exists():
        raise FileNotFoundError(f"ไม่พบ {folder} — รันขั้น export ก่อน")

    files = sorted(p for p in folder.rglob("*") if p.is_file())
    print(f"[push] repo:   {repo_id} ({'private' if private else 'PUBLIC'})")
    print(f"[push] source: {folder}")
    print(f"[push] files:  {len(files)} ({human_bytes(folder_size(folder))})")

    if dry_run:
        for path in files:
            print(f"[push]   {path.relative_to(folder)}")
        print("[push] dry run — ไม่ได้อัพอะไรขึ้นไป")
        return ""

    if "CHANGE_ME" in repo_id:
        raise ValueError(
            "ยังไม่ได้ตั้ง repo_id — แก้ใน config.yaml เป็น <hf-username>/<dataset-name>"
        )

    api = HfApi()
    print(f"[push] logged in as {api.whoami()['name']}")  # ล้มเร็วถ้ายังไม่ login
    api.create_repo(repo_id=repo_id, repo_type="dataset", private=private, exist_ok=True)
    api.upload_folder(repo_id=repo_id, repo_type="dataset",
                      folder_path=str(folder), commit_message=message)

    url = f"https://huggingface.co/datasets/{repo_id}"
    print(f"[push] done -> {url}")
    return url
