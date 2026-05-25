from __future__ import annotations

import argparse

from novel_tools import (
    DEFAULT_KNOWN_WORDS,
    DEFAULT_MAX_FORBIDDEN_UNKNOWN_TOKENS_PER_CHAPTER,
    DEFAULT_PUNCTUATION,
    build_epub,
    check_epub_structure,
    write_json,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an EPUB from a validated Chinese graded-reader manuscript.")
    parser.add_argument("--manuscript", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--known", default=str(DEFAULT_KNOWN_WORDS))
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
    parser.add_argument(
        "--max-forbidden-unknown-tokens-per-chapter",
        type=int,
        default=DEFAULT_MAX_FORBIDDEN_UNKNOWN_TOKENS_PER_CHAPTER,
    )
    parser.add_argument("--keep-spaces", action="store_true", help="Keep token spaces in the EPUB display text.")
    parser.add_argument("--no-validation-appendix", action="store_true")
    parser.add_argument("--skip-quality-gate", action="store_true", help="Debug only: build without lead quality approval.")
    parser.add_argument("--report", help="Optional JSON build report path.")
    args = parser.parse_args()

    report = build_epub(
        args.manuscript,
        args.title,
        args.out,
        known_path=args.known,
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
        max_forbidden_unknown_tokens_per_chapter=args.max_forbidden_unknown_tokens_per_chapter,
        remove_spaces=not args.keep_spaces,
        include_validation_appendix=not args.no_validation_appendix,
        require_quality_approval=not args.skip_quality_gate,
    )
    report["epub_structure"] = check_epub_structure(args.out)
    if args.report:
        write_json(args.report, report)
    print(
        "epub={epub_path} chapters={chapter_count} total_tokens={total_tokens} "
        "unique_words={unique_token_count} personal_known_tokens={personal_known_tokens} "
        "unknown_tokens={unknown_token_count} "
        "unknown_over_limit={forbidden_unknown_tokens_over_limit}".format(**report)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
