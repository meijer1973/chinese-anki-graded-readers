from __future__ import annotations

import argparse
from pathlib import Path

try:
    from novel_tools import (
        DEFAULT_KNOWN_CHARACTER_COMPOUND_LIMIT,
        DEFAULT_KNOWN_WORDS,
        DEFAULT_MARCEL_HIGH_FREQUENCY_CHARACTERS,
        DEFAULT_STRETCH_PACKS_DIR,
        ROOT,
        is_known_character_compound,
        load_known_words,
        load_optional_words,
        load_ranked_characters,
        utc_now,
        write_json,
    )
except ModuleNotFoundError:
    from scripts.novel_tools import (
        DEFAULT_KNOWN_CHARACTER_COMPOUND_LIMIT,
        DEFAULT_KNOWN_WORDS,
        DEFAULT_MARCEL_HIGH_FREQUENCY_CHARACTERS,
        DEFAULT_STRETCH_PACKS_DIR,
        ROOT,
        is_known_character_compound,
        load_known_words,
        load_optional_words,
        load_ranked_characters,
        utc_now,
        write_json,
    )


DEFAULT_OUT_DIR = ROOT / "data" / "external_agent_vocab"


def repo_relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def write_word_list(path: Path, words: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(words) + "\n", encoding="utf-8")


def stretch_pack_paths(stretch_dir: Path) -> list[Path]:
    return sorted(path for path in stretch_dir.glob("*.txt") if path.is_file())


def build_external_agent_vocab_bundle(
    *,
    known_path: Path = DEFAULT_KNOWN_WORDS,
    characters_path: Path = DEFAULT_MARCEL_HIGH_FREQUENCY_CHARACTERS,
    character_limit: int = DEFAULT_KNOWN_CHARACTER_COMPOUND_LIMIT,
    stretch_dir: Path = DEFAULT_STRETCH_PACKS_DIR,
    out_dir: Path = DEFAULT_OUT_DIR,
) -> dict:
    known_words = load_known_words(known_path)
    ranked_characters = load_ranked_characters(characters_path, character_limit)
    character_set = set(ranked_characters)

    known_words_minus_character_compounds = [
        word for word in known_words if not is_known_character_compound(word, character_set)
    ]
    known_character_compound_words = [
        word for word in known_words if is_known_character_compound(word, character_set)
    ]

    packs = stretch_pack_paths(stretch_dir)
    stretch_seen: set[str] = set()
    master_stretch_words: list[str] = []
    duplicate_stretch_words: list[dict] = []
    stretch_removed_known: list[dict] = []
    stretch_removed_character_compound: list[dict] = []
    known_set = set(known_words)

    for pack in packs:
        for word in load_optional_words(pack):
            if word in stretch_seen:
                duplicate_stretch_words.append({"word": word, "source": repo_relative(pack)})
                continue
            stretch_seen.add(word)
            if is_known_character_compound(word, character_set):
                stretch_removed_character_compound.append({"word": word, "source": repo_relative(pack)})
                continue
            if word in known_set:
                stretch_removed_known.append({"word": word, "source": repo_relative(pack)})
                continue
            master_stretch_words.append(word)

    out_dir.mkdir(parents=True, exist_ok=True)
    characters_out = out_dir / "high_frequency_characters_500.txt"
    known_out = out_dir / "known_words_minus_character_compounds.txt"
    stretch_out = out_dir / "master_stretch_words_non_core.txt"
    metadata_out = out_dir / "metadata.json"

    write_word_list(characters_out, ranked_characters)
    write_word_list(known_out, known_words_minus_character_compounds)
    write_word_list(stretch_out, master_stretch_words)

    payload = {
        "generated_at": utc_now(),
        "purpose": (
            "Compact vocabulary bundle for external writer agents drafting in Marcel personalized mode. "
            "Check high-frequency character compounds first, then compact known words, then compact non-core stretch words. "
            "Run the repository validators for final authoritative reports."
        ),
        "validation_order": [
            "Strip allowlisted punctuation from each whitespace-separated token.",
            "If every Hanzi character in the token is listed in high_frequency_characters_500.txt, classify it as high_frequency_character_compound.",
            "Otherwise exact-match known_words_minus_character_compounds.txt.",
            "Otherwise exact-match master_stretch_words_non_core.txt.",
            "Otherwise exact-match manuscript book_specific_words.txt or proper_nouns.txt when present.",
            "Otherwise report the token as a forbidden unknown.",
        ],
        "outputs": {
            "high_frequency_characters": repo_relative(characters_out),
            "known_words_minus_character_compounds": repo_relative(known_out),
            "master_stretch_words_non_core": repo_relative(stretch_out),
            "metadata": repo_relative(metadata_out),
        },
        "sources": {
            "known_words": repo_relative(known_path),
            "high_frequency_characters": repo_relative(characters_path),
            "character_limit": character_limit,
            "stretch_packs": [repo_relative(path) for path in packs],
        },
        "counts": {
            "high_frequency_character_count": len(ranked_characters),
            "known_word_count": len(known_words),
            "known_words_minus_character_compounds_count": len(known_words_minus_character_compounds),
            "known_words_covered_by_character_compounds_count": len(known_character_compound_words),
            "raw_unique_stretch_word_count": len(stretch_seen),
            "master_stretch_words_non_core_count": len(master_stretch_words),
            "stretch_words_removed_as_known_count": len(stretch_removed_known),
            "stretch_words_removed_as_character_compounds_count": len(stretch_removed_character_compound),
            "duplicate_stretch_word_count": len(duplicate_stretch_words),
        },
        "removed": {
            "known_words_covered_by_character_compounds": known_character_compound_words,
            "stretch_words_removed_as_known": stretch_removed_known,
            "stretch_words_removed_as_character_compounds": stretch_removed_character_compound,
            "duplicate_stretch_words": duplicate_stretch_words,
        },
        "final_validation_note": (
            "This bundle is optimized for external drafting and lightweight token screening. "
            "Final manuscript reports should still be generated with scripts/validate_chapter.py, "
            "scripts/validate_book.py, scripts/run_quality_gate.py, and scripts/build_epub.py using the configured repo arguments."
        ),
    }
    write_json(metadata_out, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Build compact vocabulary files for external graded-reader agents.")
    parser.add_argument("--known", default=str(DEFAULT_KNOWN_WORDS), help="Active known-word file.")
    parser.add_argument(
        "--characters",
        default=str(DEFAULT_MARCEL_HIGH_FREQUENCY_CHARACTERS),
        help="Ranked high-frequency character file.",
    )
    parser.add_argument("--character-limit", type=int, default=DEFAULT_KNOWN_CHARACTER_COMPOUND_LIMIT)
    parser.add_argument("--stretch-dir", default=str(DEFAULT_STRETCH_PACKS_DIR))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()

    payload = build_external_agent_vocab_bundle(
        known_path=Path(args.known),
        characters_path=Path(args.characters),
        character_limit=args.character_limit,
        stretch_dir=Path(args.stretch_dir),
        out_dir=Path(args.out_dir),
    )
    print(f"wrote: {payload['outputs']['high_frequency_characters']}")
    print(f"wrote: {payload['outputs']['known_words_minus_character_compounds']}")
    print(f"wrote: {payload['outputs']['master_stretch_words_non_core']}")
    print(f"wrote: {payload['outputs']['metadata']}")
    print(f"known_words_minus_character_compounds_count: {payload['counts']['known_words_minus_character_compounds_count']}")
    print(f"master_stretch_words_non_core_count: {payload['counts']['master_stretch_words_non_core_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
