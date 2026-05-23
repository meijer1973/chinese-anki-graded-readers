from __future__ import annotations

import argparse

from novel_tools import DEFAULT_KNOWN_WORDS, DEFAULT_PUNCTUATION, vocabulary_usage_report, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure vocabulary breadth for a restricted-vocabulary manuscript.")
    parser.add_argument("--known", default=str(DEFAULT_KNOWN_WORDS))
    parser.add_argument("--chapters", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--punctuation", default=str(DEFAULT_PUNCTUATION))
    parser.add_argument("--min-chapter-unique-tokens", type=int, default=0)
    parser.add_argument("--target-coverage-percent", type=float, default=0.0)
    parser.add_argument("--warn-top-20-share-above-percent", type=float, default=45.0)
    args = parser.parse_args()

    report = vocabulary_usage_report(
        args.chapters,
        args.known,
        punctuation_path=args.punctuation,
        min_chapter_unique_tokens=args.min_chapter_unique_tokens,
        target_coverage_percent=args.target_coverage_percent,
        warn_top_20_share_above_percent=args.warn_top_20_share_above_percent,
    )
    write_json(args.out, report)
    print(
        "total_tokens={total_tokens} unique_words={unique_token_count} coverage={known_word_coverage_percent}% "
        "narrow_warning={narrow_vocabulary_warning}".format(**report)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
