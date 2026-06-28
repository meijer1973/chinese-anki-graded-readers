from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import build_anki_chinese

try:
    from novel_tools import infer_stretch_layer, load_optional_words
except ModuleNotFoundError:
    from scripts.novel_tools import infer_stretch_layer, load_optional_words


DEFAULT_METADATA_DIR = ROOT / "data" / "stretch_packs" / "metadata"

PACK_DEFAULTS = {
    "general_fiction_100": {
        "part_of_speech": "fiction word",
        "example_template": "这个 {word} 很 重要 。",
        "example_en": "This {word} is important.",
        "story_affordance": "Supports emotional movement, conflict, memory, or character choice.",
    },
    "low_fantasy_150": {
        "part_of_speech": "fantasy term",
        "example_template": "这个 {word} 出现 了 。",
        "example_en": "This {word} appeared.",
        "story_affordance": "Supports a small urban-fantasy mechanism without epic lore.",
    },
    "shanghai_setting_150": {
        "part_of_speech": "setting word",
        "example_template": "林安 在 {word} 找 线索 。",
        "example_en": "Lin An looks for a clue at/in {word}.",
        "story_affordance": "Adds durable Shanghai or urban scene texture and movement.",
    },
    "professions_social_roles_100": {
        "part_of_speech": "profession/social role",
        "example_template": "{word} 告诉 林安 一个 消息 。",
        "example_en": "The {word} tells Lin An a message.",
        "story_affordance": "Gives supporting characters a social role that can affect the plot.",
    },
    "urban_objects_100": {
        "part_of_speech": "urban object",
        "example_template": "林安 看到 一个 {word} 。",
        "example_en": "Lin An sees a {word}.",
        "story_affordance": "Adds concrete objects for clues, movement, or atmosphere.",
    },
    "journalism_crime_50": {
        "part_of_speech": "journalism/crime word",
        "example_template": "林安 用 {word} 查 这个 案子 。",
        "example_en": "Lin An uses this journalism/crime clue to investigate the case.",
        "story_affordance": "Supports reporting, evidence, source protection, investigation, or case pressure.",
    },
    "business_economics_60": {
        "part_of_speech": "business/economics word",
        "example_template": "这个 {word} 会 影响 生意 。",
        "example_en": "This business factor affects the business.",
        "story_affordance": "Supports concrete scenes about shops, money, customers, prices, costs, risk, banks, and simple business decisions.",
    },
}


def load_metadata(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("words", []) if isinstance(payload, dict) else payload
    return {entry["word"]: entry for entry in entries if isinstance(entry, dict) and entry.get("word")}


def zh_tok_to_natural(text: str) -> str:
    return "".join(text.split())


def entry_english(word: str, entries_by_word: dict) -> str:
    entries = entries_by_word.get(word, [])
    if entries:
        return build_anki_chinese.concise_definitions(entries)
    return f"Needs review: {word}"


def completed_entry(word: str, pack_name: str, existing: dict, entries_by_word: dict) -> dict:
    defaults = PACK_DEFAULTS.get(
        pack_name,
        {
            "part_of_speech": "stretch word",
            "example_template": "林安 看到 {word} 。",
            "example_en": "Lin An sees {word}.",
            "story_affordance": "Adds approved story vocabulary.",
        },
    )
    example_zh_tok = existing.get("example_zh_tok") or defaults["example_template"].format(word=word)
    notes = existing.get("notes") or f"Generated starter metadata for {pack_name}; review during future curation."
    return {
        "word": word,
        "pinyin": existing.get("pinyin") or build_anki_chinese.generated_pinyin(word),
        "english": existing.get("english") or entry_english(word, entries_by_word),
        "part_of_speech": existing.get("part_of_speech") or defaults["part_of_speech"],
        "pack": existing.get("pack") or pack_name,
        "priority": existing.get("priority") or 2,
        "notes": notes,
        "example_zh_tok": example_zh_tok,
        "example_zh_natural": existing.get("example_zh_natural") or zh_tok_to_natural(example_zh_tok),
        "example_en": existing.get("example_en") or defaults["example_en"].format(word=word),
        "story_affordance": existing.get("story_affordance") or defaults["story_affordance"],
        "difficulty_note": existing.get("difficulty_note")
        or "Starter metadata; verify nuance before promoting this word into the core known list.",
        "recommended_repetition_count": existing.get("recommended_repetition_count") or 3,
    }


def complete_pack(pack_path: Path, metadata_dir: Path, entries_by_word: dict, *, dry_run: bool = False) -> dict:
    pack_name = pack_path.stem
    metadata_path = metadata_dir / f"{pack_name}.json"
    words = load_optional_words(pack_path)
    existing = load_metadata(metadata_path)
    entries = [completed_entry(word, pack_name, existing.get(word, {}), entries_by_word) for word in words]
    missing_before = [word for word in words if word not in existing]
    payload = {
        "pack": pack_name,
        "layer": infer_stretch_layer(pack_path),
        "metadata_status": "complete",
        "generated_by": "scripts/complete_stretch_pack_metadata.py",
        "words": entries,
    }
    if not dry_run:
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "pack": pack_name,
        "metadata_path": str(metadata_path),
        "word_count": len(words),
        "existing_metadata_count": len(existing),
        "missing_before_count": len(missing_before),
        "dry_run": dry_run,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Complete metadata files for stretch packs.")
    parser.add_argument("--packs", nargs="+", required=True)
    parser.add_argument("--metadata-dir", default=str(DEFAULT_METADATA_DIR))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    entries_by_word = build_anki_chinese.parse_cedict()
    metadata_dir = Path(args.metadata_dir)
    reports = [
        complete_pack(Path(pack), metadata_dir, entries_by_word, dry_run=args.dry_run)
        for pack in args.packs
    ]
    print(json.dumps({"packs": reports}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
