from __future__ import annotations

import argparse

try:
    from adaptation_tools import DEFAULT_ADAPTATIONS_DIR, RIGHTS_STATUSES, import_epub_for_adaptation
except ModuleNotFoundError:
    from scripts.adaptation_tools import DEFAULT_ADAPTATIONS_DIR, RIGHTS_STATUSES, import_epub_for_adaptation


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract an EPUB into private, stable source units for source-aligned graded-reader adaptation."
    )
    parser.add_argument("--epub", required=True, help="Path to source EPUB.")
    parser.add_argument("--slug", required=True, help="Adaptation slug under adaptations/<slug>.")
    parser.add_argument("--out-dir", default=str(DEFAULT_ADAPTATIONS_DIR), help="Adaptations root directory.")
    parser.add_argument(
        "--rights-status",
        choices=sorted(RIGHTS_STATUSES),
        default="unclear",
        help="Rights gate. Unclear/private sources should not be published as derivative tracked text.",
    )
    parser.add_argument("--min-unit-tokens", type=int, default=800)
    parser.add_argument("--max-unit-tokens", type=int, default=1500)
    parser.add_argument(
        "--copy-source-private",
        action="store_true",
        help="Copy the source EPUB into adaptations/<slug>/source_private/. This directory is gitignored.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite previously generated source units.")
    args = parser.parse_args()

    report = import_epub_for_adaptation(
        args.epub,
        args.slug,
        adaptations_dir=args.out_dir,
        rights_status=args.rights_status,
        min_unit_tokens=args.min_unit_tokens,
        max_unit_tokens=args.max_unit_tokens,
        copy_source_private=args.copy_source_private,
        force=args.force,
    )
    print(
        "adaptation={slug} units={source_unit_count} spine_items={spine_item_count} rights_status={rights_status}".format(
            **report
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
