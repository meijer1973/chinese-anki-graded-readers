from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

try:
    from novel_tools import DEFAULT_KNOWN_WORDS, ROOT, load_known_words, load_optional_words, utc_now, write_json
except ModuleNotFoundError:
    from scripts.novel_tools import DEFAULT_KNOWN_WORDS, ROOT, load_known_words, load_optional_words, utc_now, write_json


FIELDS = [
    "word",
    "pinyin",
    "meaning",
    "source",
    "status",
    "reading_confidence",
    "allow_in_personal_readers",
    "notes",
]

DEFAULT_ALLOWED_STATUSES = {"known_active", "known_passive"}
TRUTHY = {"yes", "y", "true", "1"}


def read_tsv(path: str | Path) -> list[dict]:
    tsv_path = Path(path)
    with tsv_path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        missing = [field for field in FIELDS if field not in (reader.fieldnames or [])]
        if missing:
            raise ValueError(f"{tsv_path} is missing required column(s): {', '.join(missing)}")
        return [dict(row) for row in reader if row.get("word", "").strip()]


def read_exclusions(path: str | Path | None) -> set[str]:
    if not path:
        return set()
    return set(load_optional_words(path))


def confidence_value(row: dict) -> int:
    try:
        return int(str(row.get("reading_confidence", "")).strip())
    except ValueError:
        return 0


def is_allowed_flag(row: dict) -> bool:
    return str(row.get("allow_in_personal_readers", "")).strip().lower() in TRUTHY


def sync_personal_known_words(
    *,
    profile_dir: str | Path,
    tsv_path: str | Path | None = None,
    out_path: str | Path | None = None,
    metadata_path: str | Path | None = None,
    audit_path: str | Path | None = None,
    exclusions_path: str | Path | None = None,
    core_path: str | Path = DEFAULT_KNOWN_WORDS,
    stretch_packs: list[str | Path] | None = None,
    allowed_statuses: set[str] | None = None,
    min_confidence: int = 4,
) -> dict:
    profile = Path(profile_dir)
    tsv = Path(tsv_path) if tsv_path else profile / "personal_known_words.tsv"
    out = Path(out_path) if out_path else profile / "personal_known_words.txt"
    metadata = Path(metadata_path) if metadata_path else profile / "personal_known_words.metadata.json"
    audit = Path(audit_path) if audit_path else profile / "personal_known_audit.json"
    exclusions = Path(exclusions_path) if exclusions_path else profile / "personal_known_exclusions.txt"
    allowed_statuses = allowed_statuses or DEFAULT_ALLOWED_STATUSES

    rows = read_tsv(tsv)
    core_words = set(load_known_words(core_path))
    excluded_words = read_exclusions(exclusions)
    stretch_words: set[str] = set()
    for pack in stretch_packs or []:
        stretch_words.update(load_optional_words(pack))

    generated_words: list[str] = []
    generated_seen: set[str] = set()
    metadata_rows: list[dict] = []
    duplicate_personal: list[str] = []
    excluded_by_status: list[str] = []
    excluded_by_confidence: list[str] = []
    excluded_by_flag: list[str] = []
    excluded_by_exclusion_file: list[str] = []
    duplicate_as_core: list[str] = []
    duplicate_as_stretch: list[str] = []

    for index, raw_row in enumerate(rows, start=2):
        word = raw_row["word"].strip()
        row = {field: str(raw_row.get(field, "")).strip() for field in FIELDS}
        row["word"] = word
        row["source_line"] = index
        row["reading_confidence"] = confidence_value(row)
        status = row["status"]
        include_reason = "included"
        allowed = True

        if word in generated_seen:
            duplicate_personal.append(word)
            allowed = False
            include_reason = "duplicate_personal"
        elif word in excluded_words:
            excluded_by_exclusion_file.append(word)
            allowed = False
            include_reason = "excluded_file"
        elif status not in allowed_statuses:
            excluded_by_status.append(word)
            allowed = False
            include_reason = "status"
        elif row["reading_confidence"] < min_confidence:
            excluded_by_confidence.append(word)
            allowed = False
            include_reason = "confidence"
        elif not is_allowed_flag(row):
            excluded_by_flag.append(word)
            allowed = False
            include_reason = "allow_flag"
        elif word in core_words:
            duplicate_as_core.append(word)
            allowed = False
            include_reason = "already_core"

        if allowed:
            generated_words.append(word)
            generated_seen.add(word)
            if word in stretch_words:
                duplicate_as_stretch.append(word)

        row["included_in_personal_known_words_txt"] = allowed
        row["inclusion_reason"] = include_reason
        row["already_core"] = word in core_words
        row["also_in_stretch_pack"] = word in stretch_words
        metadata_rows.append(row)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(generated_words) + ("\n" if generated_words else ""), encoding="utf-8")
    if not exclusions.exists():
        exclusions.parent.mkdir(parents=True, exist_ok=True)
        exclusions.write_text("# One excluded personal-known word per line.\n", encoding="utf-8")

    payload = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "profile_name": profile.name,
        "profile_dir": str(profile),
        "source_tsv_path": str(tsv),
        "generated_word_list_path": str(out),
        "core_known_words_path": str(Path(core_path)),
        "exclusions_path": str(exclusions),
        "policy": {
            "allowed_statuses": sorted(allowed_statuses),
            "min_reading_confidence": min_confidence,
            "allow_in_personal_readers_required": True,
            "core_duplicates_count_as_core_not_personal": True,
            "personal_known_is_not_stretch": True,
        },
        "word_count": len(metadata_rows),
        "generated_personal_known_word_count": len(generated_words),
        "words": metadata_rows,
    }
    metadata.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    audit_payload = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "profile_name": profile.name,
        "source_tsv_path": str(tsv),
        "generated_word_list_path": str(out),
        "row_count": len(rows),
        "generated_personal_known_word_count": len(generated_words),
        "core_duplicate_count": len(set(duplicate_as_core)),
        "stretch_overlap_count": len(set(duplicate_as_stretch)),
        "duplicate_personal_count": len(set(duplicate_personal)),
        "excluded_by_status_count": len(set(excluded_by_status)),
        "excluded_by_confidence_count": len(set(excluded_by_confidence)),
        "excluded_by_flag_count": len(set(excluded_by_flag)),
        "excluded_by_exclusion_file_count": len(set(excluded_by_exclusion_file)),
        "core_duplicates": sorted(set(duplicate_as_core)),
        "stretch_overlaps": sorted(set(duplicate_as_stretch)),
        "duplicate_personal": sorted(set(duplicate_personal)),
        "excluded_by_status": sorted(set(excluded_by_status)),
        "excluded_by_confidence": sorted(set(excluded_by_confidence)),
        "excluded_by_flag": sorted(set(excluded_by_flag)),
        "excluded_by_exclusion_file": sorted(set(excluded_by_exclusion_file)),
    }
    write_json(audit, audit_payload)
    return audit_payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a validator-ready personal-known word list from a learner-profile TSV.")
    parser.add_argument("--profile", default=str(ROOT / "data" / "learner_profiles" / "marcel"))
    parser.add_argument("--tsv")
    parser.add_argument("--out")
    parser.add_argument("--metadata")
    parser.add_argument("--audit")
    parser.add_argument("--exclusions")
    parser.add_argument("--core", default=str(DEFAULT_KNOWN_WORDS))
    parser.add_argument("--stretch-pack", action="append", default=[])
    parser.add_argument("--min-confidence", type=int, default=4)
    parser.add_argument("--statuses", nargs="+", default=sorted(DEFAULT_ALLOWED_STATUSES))
    args = parser.parse_args()

    report = sync_personal_known_words(
        profile_dir=args.profile,
        tsv_path=args.tsv,
        out_path=args.out,
        metadata_path=args.metadata,
        audit_path=args.audit,
        exclusions_path=args.exclusions,
        core_path=args.core,
        stretch_packs=args.stretch_pack,
        allowed_statuses=set(args.statuses),
        min_confidence=args.min_confidence,
    )
    print(
        "profile={profile_name} generated={generated_personal_known_word_count} "
        "core_duplicates={core_duplicate_count} stretch_overlaps={stretch_overlap_count}".format(**report)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
