"""รัน ELT ครบทุกขั้น: extract -> load -> transform -> export

ขั้น publish ไม่รวมอยู่ในนี้ (เป็นการอัพขึ้นเน็ต ต้องสั่งเอง):
    python -m elt.publish
"""

from elt import export, extract, load, transform


def main() -> None:
    extract.main()
    load.main()
    transform.main()
    export.main()
    print("\nขั้นต่อไป: ตรวจ data/elt_export/README.md แล้วรัน `python -m elt.publish`")


if __name__ == "__main__":
    main()
