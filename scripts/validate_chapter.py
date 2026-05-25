from __future__ import annotations

import argparse

from novel_tools import (
    DEFAULT_KNOWN_WORDS,
    DEFAULT_MAX_FORBIDDEN_UNKNOWN_TOKENS_PER_CHAPTER,
    DEFAULT_PUNCTUATION,
    validate_chapter,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate one space-tokenized Chinese chapter against known words.")
    parser.add_argument("--known", default=str(DEFAULT_KNOWN_WORDS))
    parser.add_argument("--chapter", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--punctuation", default=str(DEFAULT_PUNCTUATION))
    parser.add_argument("--personal-known", help="Optional learner-profile personal-known word list.")
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
    parser.add_argument(
        "--max-forbidden-unknown-tokens-per-chapter",
        type=int,
        default=DEFAULT_MAX_FORBIDDEN_UNKNOWN_TOKENS_PER_CHAPTER,
        help="Validation passes when forbidden unknown tokens in this chapter are at or below this number.",
    )
    args = parser.parse_args()

    report = validate_chapter(
        args.chapter,
        args.known,
        punctuation_path=args.punctuation,
        personal_known_words_path=args.personal_known,
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
        max_forbidden_unknown_tokens_per_chapter=args.max_forbidden_unknown_tokens_per_chapter,
    )
    write_json(args.out, report)
    print(
        "valid={valid} total_tokens={total_tokens} unique_words={unique_token_count} "
        "vocabulary_profile={vocabulary_profile} personal_known_tokens={personal_known_tokens} "
        "unknown_tokens={unknown_token_count} unknown_over_limit={forbidden_unknown_tokens_over_limit} "
        "stretch_percent={stretch_token_percent}".format(**report)
    )
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
