from __future__ import annotations

import argparse
import json
from pathlib import Path

from novel_tools import ROOT, utc_now


DEFAULT_GRADED_READER_SOURCE = ROOT / "High frequency words 0-10000.txt"


def read_ranked_words(source: Path) -> list[str]:
    words: list[str] = []
    seen: set[str] = set()
    for line_number, raw_line in enumerate(source.read_text(encoding="utf-8-sig").splitlines(), start=1):
        word = raw_line.strip()
        if not word:
            continue
        if word in seen:
            raise ValueError(f"Duplicate word {word!r} in {source} line {line_number}")
        seen.add(word)
        words.append(word)
    if not words:
        raise ValueError(f"No words found in {source}")
    return words


def sync_known_words(source: Path, out: Path, limit: int, metadata: Path | None = None) -> dict:
    ranked_words = read_ranked_words(source)
    if limit <= 0:
        selected = ranked_words
    else:
        selected = ranked_words[:limit]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(selected) + "\n", encoding="utf-8")
    payload = {
        "generated_at": utc_now(),
        "source_path": str(source),
        "output_path": str(out),
        "source_word_count": len(ranked_words),
        "known_word_count": len(selected),
        "limit": limit,
        "derivation": (
            "First N ranked entries from High frequency words 0-10000.txt. "
            "This graded-reader source is separate from word list chinese.txt, "
            "which remains the Anki deck source."
        ),
    }
    if metadata:
        metadata.parent.mkdir(parents=True, exist_ok=True)
        metadata.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate data/known_words.txt from the graded-reader ranked word list.")
    parser.add_argument(
        "--source",
        default=str(DEFAULT_GRADED_READER_SOURCE),
        help="Ranked graded-reader word source. Defaults to High frequency words 0-10000.txt.",
    )
    parser.add_argument("--out", default=str(ROOT / "data" / "known_words.txt"))
    parser.add_argument("--limit", type=int, default=3500, help="Number of ranked words to mark known. Use 0 for all words.")
    parser.add_argument("--metadata", default=str(ROOT / "data" / "known_words.metadata.json"))
    args = parser.parse_args()

    payload = sync_known_words(Path(args.source), Path(args.out), args.limit, Path(args.metadata) if args.metadata else None)
    print(f"wrote: {payload['output_path']}")
    print(f"known_word_count: {payload['known_word_count']}")
    print(f"source_word_count: {payload['source_word_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
