from __future__ import annotations

import argparse
from pathlib import Path

from novel_tools import (
    DEFAULT_KNOWN_CHARACTER_COMPOUND_LIMIT,
    DEFAULT_KNOWN_WORDS,
    DEFAULT_MARCEL_HIGH_FREQUENCY_CHARACTERS,
    DEFAULT_MAX_FORBIDDEN_UNKNOWN_TOKENS_PER_CHAPTER,
    DEFAULT_PUNCTUATION,
    chapter_files,
    validate_book,
    validate_chapter,
    write_json,
)


def validation_report_path(chapter: Path) -> Path:
    if chapter.name.endswith(".zh-tok.txt"):
        return chapter.with_name(chapter.name.replace(".zh-tok.txt", ".validation.json"))
    return chapter.with_suffix(".validation.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate per-chapter and whole-book vocabulary reports for a manuscript.")
    parser.add_argument("--manuscript", required=True)
    parser.add_argument("--known", default=str(DEFAULT_KNOWN_WORDS))
    parser.add_argument("--punctuation", default=str(DEFAULT_PUNCTUATION))
    parser.add_argument("--personal-known", help="Optional learner-profile personal-known word list.")
    parser.add_argument(
        "--known-character-compounds",
        nargs="?",
        const=str(DEFAULT_MARCEL_HIGH_FREQUENCY_CHARACTERS),
        default=None,
        metavar="PATH",
        help="Enable the derived high-frequency-character compound layer; defaults to Marcel's ranked character list.",
    )
    parser.add_argument(
        "--known-character-compound-limit",
        type=int,
        default=DEFAULT_KNOWN_CHARACTER_COMPOUND_LIMIT,
        help="Number of ranked characters to use for the derived compound layer. Use 0 for all.",
    )
    parser.add_argument("--general-fiction-pack")
    parser.add_argument("--genre-pack")
    parser.add_argument("--setting-pack")
    parser.add_argument("--profession-pack")
    parser.add_argument("--journalism-crime-pack")
    parser.add_argument("--urban-objects-pack")
    parser.add_argument("--book-specific")
    parser.add_argument("--proper-nouns")
    parser.add_argument("--extra-pack", action="append", default=[])
    parser.add_argument(
        "--max-forbidden-unknown-tokens-per-chapter",
        type=int,
        default=DEFAULT_MAX_FORBIDDEN_UNKNOWN_TOKENS_PER_CHAPTER,
    )
    args = parser.parse_args()

    manuscript = Path(args.manuscript)
    chapters_dir = manuscript / "chapters"
    layered_args = {
        "general_fiction_pack": args.general_fiction_pack,
        "personal_known_words_path": args.personal_known,
        "known_character_compounds_path": args.known_character_compounds,
        "known_character_compound_limit": args.known_character_compound_limit,
        "genre_pack": args.genre_pack,
        "setting_pack": args.setting_pack,
        "profession_pack": args.profession_pack,
        "journalism_crime_pack": args.journalism_crime_pack,
        "urban_objects_pack": args.urban_objects_pack,
        "book_specific_words_path": args.book_specific,
        "proper_nouns_path": args.proper_nouns,
        "extra_packs": args.extra_pack,
        "max_forbidden_unknown_tokens_per_chapter": args.max_forbidden_unknown_tokens_per_chapter,
    }
    for chapter in chapter_files(chapters_dir):
        report = validate_chapter(chapter, args.known, punctuation_path=args.punctuation, **layered_args)
        write_json(validation_report_path(chapter), report)

    book_report = validate_book(chapters_dir, args.known, punctuation_path=args.punctuation, **layered_args)
    write_json(manuscript / "vocabulary_report.json", book_report)
    print(
        "valid={valid} chapters={chapter_count} total_tokens={total_tokens} "
        "unique_words={unique_token_count} vocabulary_profile={vocabulary_profile} "
        "personal_known_tokens={personal_known_tokens} "
        "high_frequency_character_compound_tokens={high_frequency_character_compound_tokens} "
        "unknown_tokens={unknown_token_count} "
        "unknown_over_limit={forbidden_unknown_tokens_over_limit}".format(**book_report)
    )
    return 0 if book_report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
