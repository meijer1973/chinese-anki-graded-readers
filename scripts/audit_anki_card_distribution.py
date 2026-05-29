from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.anki_card_distribution import (  # noqa: E402
    DEFAULT_RUN_THRESHOLD,
    DEFAULT_WINDOW_SIZES,
    WORD_LIST,
    audit_distribution,
    audit_passes,
    dump_json,
    markdown_audit_report,
    read_word_list,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit single-character clumping in the Chinese Anki source list.")
    parser.add_argument("--word-list", type=Path, default=WORD_LIST, help="Word list to audit.")
    parser.add_argument("--threshold", type=int, default=DEFAULT_RUN_THRESHOLD, help="Report single-character runs longer than this.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of Markdown.")
    parser.add_argument("--out", type=Path, help="Optional output file.")
    parser.add_argument("--fail-on-problem", action="store_true", help="Exit nonzero when the active limits are violated.")
    parser.add_argument("--max-single-run", type=int, default=1, help="Limit used with --fail-on-problem.")
    parser.add_argument("--window-size", type=int, default=20, help="Window size used with --fail-on-problem.")
    parser.add_argument("--max-single-per-window", type=int, default=10, help="Window max used with --fail-on-problem.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    words = read_word_list(args.word_list)
    audit = audit_distribution(words, run_threshold=args.threshold, window_sizes=DEFAULT_WINDOW_SIZES)
    output = dump_json(audit) + "\n" if args.json else markdown_audit_report(audit)

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    else:
        print(output, end="")

    if args.fail_on_problem and not audit_passes(
        audit,
        max_single_run=args.max_single_run,
        window_size=args.window_size,
        max_single_per_window=args.max_single_per_window,
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
