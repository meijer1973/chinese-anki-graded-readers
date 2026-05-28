from __future__ import annotations

import argparse

try:
    from adaptation_tools import profile_adaptation_vocabulary
    from novel_tools import DEFAULT_KNOWN_WORDS, DEFAULT_PUNCTUATION
except ModuleNotFoundError:
    from scripts.adaptation_tools import profile_adaptation_vocabulary
    from scripts.novel_tools import DEFAULT_KNOWN_WORDS, DEFAULT_PUNCTUATION


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Profile EPUB adaptation source units against the graded-reader vocabulary layers."
    )
    parser.add_argument("--adaptation", required=True, help="Path to adaptations/<slug>.")
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
    parser.add_argument("--target-readable-coverage-percent", type=float, default=98.0)
    parser.add_argument(
        "--include-non-hanzi-unknowns",
        action="store_true",
        help="Count Latin, pinyin, number, and URL tokens as unknowns in source profiling. By default they are reported separately.",
    )
    args = parser.parse_args()

    report = profile_adaptation_vocabulary(
        args.adaptation,
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
        target_readable_coverage_percent=args.target_readable_coverage_percent,
        ignore_non_hanzi_unknowns=not args.include_non_hanzi_unknowns,
    )
    print(
        "adaptation={adaptation_dir} units={unit_count} total_tokens={total_tokens} "
        "coverage={readable_coverage_percent}% unknown={forbidden_unknown_tokens} "
        "next={recommended_next_step}".format(**report)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
