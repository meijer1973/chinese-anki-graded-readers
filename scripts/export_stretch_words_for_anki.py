from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

try:
    from novel_tools import DEFAULT_KNOWN_WORDS, infer_stretch_layer, load_known_words, load_optional_words, write_json
except ModuleNotFoundError:
    from scripts.novel_tools import DEFAULT_KNOWN_WORDS, infer_stretch_layer, load_known_words, load_optional_words, write_json


FIELDS = [
    "Hanzi",
    "Pinyin",
    "English",
    "PartOfSpeech",
    "Pack",
    "Layer",
    "Priority",
    "SourceBook",
    "FirstChapter",
    "ExampleSentenceZhTok",
    "ExampleSentenceZhNatural",
    "ExampleSentenceEnglish",
    "Status",
    "Notes",
]


def read_existing_words(path: str | Path | None) -> set[str]:
    if not path:
        return set()
    existing_path = Path(path)
    if not existing_path.exists():
        return set()
    lines = [line for line in existing_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return set()
    first = lines[0].split("\t")
    header = {item.strip().lower(): index for index, item in enumerate(first)}
    word_index = header.get("hanzi", header.get("word", 0))
    start = 1 if any(name in header for name in ("hanzi", "word")) else 0
    words: set[str] = set()
    for line in lines[start:]:
        parts = line.split("\t")
        if word_index < len(parts) and parts[word_index].strip():
            words.add(parts[word_index].strip())
    return words


def load_pack_metadata(metadata_dir: str | Path | None, pack_path: str | Path) -> dict[str, dict]:
    if not metadata_dir:
        return {}
    metadata_path = Path(metadata_dir) / f"{Path(pack_path).stem}.json"
    if not metadata_path.exists():
        return {}
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        entries = payload.get("words", [])
    else:
        entries = payload
    return {entry["word"]: entry for entry in entries if isinstance(entry, dict) and entry.get("word")}


def zh_tok_to_natural(text: str) -> str:
    return "".join(text.split())


def metadata_notes(meta: dict) -> str:
    extra_keys = ("story_affordance", "difficulty_note", "recommended_repetition_count")
    if meta.get("notes") and not any(meta.get(key) not in (None, "") for key in extra_keys):
        return str(meta["notes"])
    parts = []
    for key, label in (
        ("notes", "Notes"),
        ("story_affordance", "Story affordance"),
        ("difficulty_note", "Difficulty"),
        ("recommended_repetition_count", "Recommended repetitions"),
    ):
        value = meta.get(key)
        if value not in (None, ""):
            parts.append(f"{label}: {value}")
    return " | ".join(parts)


def export_candidates(
    packs: list[str | Path],
    *,
    core_path: str | Path = DEFAULT_KNOWN_WORDS,
    existing_anki_path: str | Path | None = None,
    metadata_dir: str | Path | None = None,
    out_path: str | Path,
    dry_run: bool = False,
) -> dict:
    core_words = set(load_known_words(core_path))
    existing_words = read_existing_words(existing_anki_path)
    seen: set[str] = set()
    rows: list[dict] = []
    duplicates: list[dict] = []
    excluded_core: list[str] = []
    excluded_existing: list[str] = []
    missing_metadata: list[dict] = []

    for pack in packs:
        pack_path = Path(pack)
        pack_name = pack_path.stem
        layer = infer_stretch_layer(pack_path)
        metadata = load_pack_metadata(metadata_dir, pack_path)
        for word in load_optional_words(pack_path):
            if word in core_words:
                excluded_core.append(word)
                continue
            if word in existing_words:
                excluded_existing.append(word)
                continue
            if word in seen:
                duplicates.append({"word": word, "ignored_pack": pack_name})
                continue
            seen.add(word)
            meta = metadata.get(word, {})
            if not meta:
                missing_metadata.append({"word": word, "pack": pack_name})
            example_zh_tok = meta.get("example_zh_tok", "")
            rows.append(
                {
                    "Hanzi": word,
                    "Pinyin": meta.get("pinyin", ""),
                    "English": meta.get("english", ""),
                    "PartOfSpeech": meta.get("part_of_speech", ""),
                    "Pack": meta.get("pack", pack_name),
                    "Layer": layer,
                    "Priority": meta.get("priority", ""),
                    "SourceBook": "",
                    "FirstChapter": "",
                    "ExampleSentenceZhTok": example_zh_tok,
                    "ExampleSentenceZhNatural": zh_tok_to_natural(example_zh_tok),
                    "ExampleSentenceEnglish": meta.get("example_en", ""),
                    "Status": "candidate",
                    "Notes": metadata_notes(meta),
                }
            )

    output = Path(out_path)
    if not dry_run:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    return {
        "out_path": str(output),
        "dry_run": dry_run,
        "candidate_count": len(rows),
        "excluded_core_count": len(set(excluded_core)),
        "excluded_existing_anki_count": len(set(excluded_existing)),
        "duplicate_count": len(duplicates),
        "missing_metadata_count": len(missing_metadata),
        "duplicates": duplicates,
        "missing_metadata": missing_metadata,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export approved stretch words as Anki review candidates.")
    parser.add_argument("--packs", nargs="+", required=True)
    parser.add_argument("--metadata")
    parser.add_argument("--existing-anki")
    parser.add_argument("--core", default=str(DEFAULT_KNOWN_WORDS))
    parser.add_argument("--out", required=True)
    parser.add_argument("--report")
    parser.add_argument("--dry-run", action="store_true", help="Collect and report candidates without writing the TSV.")
    args = parser.parse_args()

    report = export_candidates(
        args.packs,
        core_path=args.core,
        existing_anki_path=args.existing_anki,
        metadata_dir=args.metadata,
        out_path=args.out,
        dry_run=args.dry_run,
    )
    if args.report:
        write_json(args.report, report)
    print(
        "candidates={candidate_count} excluded_core={excluded_core_count} "
        "duplicates={duplicate_count} missing_metadata={missing_metadata_count}".format(**report)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
