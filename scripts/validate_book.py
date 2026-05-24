from __future__ import annotations

import argparse

from novel_tools import (
    DEFAULT_KNOWN_WORDS,
    DEFAULT_MAX_FORBIDDEN_UNKNOWN_TOKENS_PER_CHAPTER,
    DEFAULT_PUNCTUATION,
    validate_book,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a directory of space-tokenized Chinese chapters.")
    parser.add_argument("--known", default=str(DEFAULT_KNOWN_WORDS))
    parser.add_argument("--chapters", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--punctuation", default=str(DEFAULT_PUNCTUATION))
    parser.add_argument("--general-fiction-pack")
    parser.add_argument("--genre-pack")
    parser.add_argument("--setting-pack")
    parser.add_argument("--profession-pack")
    parser.add_argument("--journalism-crime-pack")
    parser.add_argument("--urban-objects-pack")
    parser.add_argument("--book-specific")
    parser.add_argument("--proper-nouns")
    parser.add_argument("--extra-pack", action="append", default=[])
    parser.add_argument("--target-core-coverage-percent", type=float)
    parser.add_argument("--max-total-stretch-token-percent", type=float)
    parser.add_argument("--max-new-stretch-words-per-chapter", type=int)
    parser.add_argument(
        "--max-forbidden-unknown-tokens-per-chapter",
        type=int,
        default=DEFAULT_MAX_FORBIDDEN_UNKNOWN_TOKENS_PER_CHAPTER,
        help="Validation passes when each chapter is at or below this forbidden-unknown token budget.",
    )
    args = parser.parse_args()

    report = validate_book(
        args.chapters,
        args.known,
        punctuation_path=args.punctuation,
        general_fiction_pack=args.general_fiction_pack,
        genre_pack=args.genre_pack,
        setting_pack=args.setting_pack,
        profession_pack=args.profession_pack,
        journalism_crime_pack=args.journalism_crime_pack,
        urban_objects_pack=args.urban_objects_pack,
        book_specific_words_path=args.book_specific,
        proper_nouns_path=args.proper_nouns,
        extra_packs=args.extra_pack,
        target_core_coverage_percent=args.target_core_coverage_percent,
        max_total_stretch_token_percent=args.max_total_stretch_token_percent,
        max_new_stretch_words_per_chapter=args.max_new_stretch_words_per_chapter,
        max_forbidden_unknown_tokens_per_chapter=args.max_forbidden_unknown_tokens_per_chapter,
    )
    write_json(args.out, report)
    print(
        "valid={valid} chapters={chapter_count} total_tokens={total_tokens} "
        "unique_words={unique_token_count} unknown_tokens={unknown_token_count} "
        "unknown_over_limit={forbidden_unknown_tokens_over_limit} "
        "stretch_percent={stretch_token_percent}".format(**report)
    )
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
