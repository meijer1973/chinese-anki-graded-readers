from __future__ import annotations

import argparse
import csv
from pathlib import Path

try:
    from novel_tools import load_known_words, load_optional_words, write_json
except ModuleNotFoundError:
    from scripts.novel_tools import load_known_words, load_optional_words, write_json


def read_approved_words(path: str | Path) -> list[str]:
    approved_path = Path(path)
    lines = [line for line in approved_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return []
    if "\t" in lines[0]:
        rows = list(csv.DictReader(lines, delimiter="\t"))
        if rows:
            field = "Hanzi" if "Hanzi" in rows[0] else "Word" if "Word" in rows[0] else None
            if field:
                return [row[field].strip() for row in rows if row.get(field, "").strip()]
    return [line.split("\t", 1)[0].strip() for line in lines if line.split("\t", 1)[0].strip()]


def load_stretch_pack_words(path: str | Path) -> set[str]:
    pack_path = Path(path)
    if pack_path.is_dir():
        words: set[str] = set()
        for txt in sorted(pack_path.glob("*.txt")):
            words.update(load_optional_words(txt))
        return words
    return set(load_optional_words(pack_path))


def promote_words(
    approved_path: str | Path,
    *,
    core_path: str | Path,
    stretch_pack_paths: list[str | Path],
    out_path: str | Path,
    audit_path: str | Path | None = None,
    dry_run: bool = False,
) -> dict:
    core_words = load_known_words(core_path)
    core_set = set(core_words)
    stretch_words: set[str] = set()
    for path in stretch_pack_paths:
        stretch_words.update(load_stretch_pack_words(path))

    approved_words = read_approved_words(approved_path)
    promoted: list[str] = []
    already_core: list[str] = []
    not_in_stretch_packs: list[str] = []
    seen: set[str] = set()
    for word in approved_words:
        if word in seen:
            continue
        seen.add(word)
        if word in core_set:
            already_core.append(word)
            continue
        if stretch_words and word not in stretch_words:
            not_in_stretch_packs.append(word)
            continue
        promoted.append(word)

    output = Path(out_path)
    if not dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("\n".join(core_words + promoted) + "\n", encoding="utf-8")

    report = {
        "core_path": str(Path(core_path)),
        "out_path": str(output),
        "dry_run": dry_run,
        "approved_count": len(approved_words),
        "promoted_count": len(promoted),
        "already_core": already_core,
        "not_in_stretch_packs": not_in_stretch_packs,
        "promoted_words": promoted,
        "note": "Historical manuscript reports are not modified. Future books can use the updated known list as core.",
    }
    if audit_path:
        write_json(audit_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote reviewed stretch words into a new core known-word file.")
    parser.add_argument("--approved", required=True)
    parser.add_argument("--core", required=True)
    parser.add_argument("--stretch-packs", nargs="+", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--audit")
    parser.add_argument("--dry-run", action="store_true", help="Report promotions without writing the updated known-word file.")
    args = parser.parse_args()

    report = promote_words(
        args.approved,
        core_path=args.core,
        stretch_pack_paths=args.stretch_packs,
        out_path=args.out,
        audit_path=args.audit,
        dry_run=args.dry_run,
    )
    print(
        "approved={approved_count} promoted={promoted_count} already_core={already_core_count}".format(
            already_core_count=len(report["already_core"]),
            **report,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
