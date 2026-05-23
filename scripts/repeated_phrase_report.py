from __future__ import annotations

import argparse

from novel_tools import DEFAULT_PUNCTUATION, repeated_phrase_report, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Report repeated 2-4 token phrases in tokenized Chinese chapters.")
    parser.add_argument("--chapters", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--punctuation", default=str(DEFAULT_PUNCTUATION))
    parser.add_argument("--min-count", type=int, default=3)
    args = parser.parse_args()

    report = repeated_phrase_report(args.chapters, punctuation_path=args.punctuation, min_count=args.min_count)
    write_json(args.out, report)
    print(
        "repeated_phrases={count} warning={warning}".format(
            count=len(report["repeated_phrases"]),
            warning=report["phrase_repetition_warning"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
