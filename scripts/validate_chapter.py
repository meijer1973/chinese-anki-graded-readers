from __future__ import annotations

import argparse

from novel_tools import (
    DEFAULT_EASY_CHARACTER_COMPOUND_LIMIT,
    DEFAULT_KNOWN_CHARACTER_COMPOUND_LIMIT,
    DEFAULT_KNOWN_WORDS,
    DEFAULT_MARCEL_HIGH_FREQUENCY_CHARACTERS,
    DEFAULT_MAX_EASY_CHARACTER_COMPOUND_TOKEN_PERCENT,
    DEFAULT_MAX_TOTAL_STRETCH_TOKEN_PERCENT,
    DEFAULT_MAX_FORBIDDEN_UNKNOWN_TOKENS_PER_CHAPTER,
    DEFAULT_MIN_KNOWN_TOKEN_PERCENT,
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
    parser.add_argument(
        "--easy-character-compounds",
        default=str(DEFAULT_MARCEL_HIGH_FREQUENCY_CHARACTERS),
        help="Ranked character list used for the minimum-difficulty first-N character-compound ceiling.",
    )
    parser.add_argument(
        "--easy-character-compound-limit",
        type=int,
        default=DEFAULT_EASY_CHARACTER_COMPOUND_LIMIT,
        help="Number of ranked characters treated as the easy character-compound band.",
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
    parser.add_argument("--target-core-coverage-percent", type=float)
    parser.add_argument(
        "--min-known-token-percent",
        type=float,
        default=DEFAULT_MIN_KNOWN_TOKEN_PERCENT,
        help="Require at least this percentage of tokens to be known/personal-known/known-character compounds.",
    )
    parser.add_argument(
        "--max-total-stretch-token-percent",
        type=float,
        default=DEFAULT_MAX_TOTAL_STRETCH_TOKEN_PERCENT,
        help="Require approved non-core tokens, including stretch layers and proper nouns, at or below this percentage.",
    )
    parser.add_argument(
        "--max-easy-character-compound-token-percent",
        type=float,
        default=DEFAULT_MAX_EASY_CHARACTER_COMPOUND_TOKEN_PERCENT,
        help="Require tokens made only from the first easy-character band to stay at or below this percentage.",
    )
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
        known_character_compounds_path=args.known_character_compounds,
        known_character_compound_limit=args.known_character_compound_limit,
        easy_character_compounds_path=args.easy_character_compounds,
        easy_character_compound_limit=args.easy_character_compound_limit,
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
        min_known_token_percent=args.min_known_token_percent,
        max_total_stretch_token_percent=args.max_total_stretch_token_percent,
        max_easy_character_compound_token_percent=args.max_easy_character_compound_token_percent,
        max_forbidden_unknown_tokens_per_chapter=args.max_forbidden_unknown_tokens_per_chapter,
    )
    write_json(args.out, report)
    print(
        "valid={valid} total_tokens={total_tokens} unique_words={unique_token_count} "
        "vocabulary_profile={vocabulary_profile} personal_known_tokens={personal_known_tokens} "
        "high_frequency_character_compound_tokens={high_frequency_character_compound_tokens} "
        "known_percent={known_token_percent} known_percent_ok={known_token_percent_allowed} "
        "unknown_tokens={unknown_token_count} unknown_over_limit={forbidden_unknown_tokens_over_limit} "
        "stretch_percent={stretch_token_percent} stretch_percent_ok={stretch_token_percent_allowed} "
        "easy_character_compound_percent={easy_character_compound_token_percent} "
        "easy_character_compound_percent_ok={easy_character_compound_token_percent_allowed}".format(**report)
    )
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
