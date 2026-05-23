from __future__ import annotations

import argparse
import json

from novel_tools import DEFAULT_KNOWN_WORDS, load_known_words


def main() -> int:
    parser = argparse.ArgumentParser(description="Load and summarize a known-word list.")
    parser.add_argument("--known", default=str(DEFAULT_KNOWN_WORDS))
    parser.add_argument("--json", action="store_true", help="Print a JSON summary.")
    args = parser.parse_args()

    words = load_known_words(args.known)
    payload = {
        "known_words_path": args.known,
        "known_word_count": len(words),
        "first_word": words[0],
        "last_word": words[-1],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"known_words_path: {payload['known_words_path']}")
        print(f"known_word_count: {payload['known_word_count']}")
        print(f"first_word: {payload['first_word']}")
        print(f"last_word: {payload['last_word']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
