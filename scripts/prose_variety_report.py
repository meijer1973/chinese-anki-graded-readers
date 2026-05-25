from __future__ import annotations

import argparse

try:
    from novel_tools import DEFAULT_PUNCTUATION, prose_variety_report, write_json
except ModuleNotFoundError:
    from scripts.novel_tools import DEFAULT_PUNCTUATION, prose_variety_report, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Report prose-variety risks in tokenized Chinese chapters.")
    parser.add_argument("--chapters", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--punctuation", default=str(DEFAULT_PUNCTUATION))
    parser.add_argument("--dialogue-tag-warning-count", type=int, default=10)
    parser.add_argument("--phrase-warning-count", type=int, default=8)
    parser.add_argument("--sentence-frame-warning-count", type=int, default=5)
    args = parser.parse_args()

    report = prose_variety_report(
        args.chapters,
        punctuation_path=args.punctuation,
        dialogue_tag_warning_count=args.dialogue_tag_warning_count,
        phrase_warning_count=args.phrase_warning_count,
        sentence_frame_warning_count=args.sentence_frame_warning_count,
    )
    write_json(args.out, report)
    print(
        "style_revision_required={required} warnings={warnings} repeated_dialogue_tags={tags}".format(
            required=report["style_revision_required"],
            warnings=len(report["warnings"]),
            tags=len(report["repeated_dialogue_tags"]),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
