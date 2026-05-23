from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import add_missing_single_character_notes as character_add
import build_anki_chinese
import setup_production_sentence_cards


ROOT = Path(__file__).resolve().parent
WORD_LIST = ROOT / "word list chinese.txt"
SOURCE_TSV = ROOT / "anki_chinese_review.tsv"
WORD_LIST_BACKUP = ROOT / "word_list_before_character_closure_backup.txt"
APPLIED_TSV = ROOT / "single_character_notes_policy_added.tsv"
REPORT_MD = ROOT / "single_character_notes_policy_report.md"


def is_hanzi(char: str) -> bool:
    return "\u3400" <= char <= "\u9fff" or "\uf900" <= char <= "\ufaff"


def hanzi_chars(text: str) -> list[str]:
    return [char for char in text if is_hanzi(char)]


def read_words() -> list[str]:
    return [line.strip() for line in WORD_LIST.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def priority(first_rank: int) -> str:
    if first_rank <= 500:
        return "high"
    if first_rank <= 1000:
        return "medium"
    return "low"


def missing_character_rows(words: list[str]) -> list[dict[str, str]]:
    single_char_notes = {
        word
        for word in words
        if len(hanzi_chars(word)) == 1 and "".join(hanzi_chars(word)) == word
    }
    char_words: dict[str, list[tuple[int, str]]] = defaultdict(list)
    first_rank: dict[str, int] = {}

    for rank, word in enumerate(words, start=1):
        chars = hanzi_chars(word)
        if len(chars) < 2:
            continue

        seen_in_word: list[str] = []
        for char in chars:
            if char not in seen_in_word:
                seen_in_word.append(char)

        for char in seen_in_word:
            if char in single_char_notes:
                continue
            char_words[char].append((rank, word))
            first_rank.setdefault(char, rank)

    rows: list[dict[str, str]] = []
    for char in sorted(char_words, key=lambda item: (first_rank[item], item)):
        samples = char_words[char]
        rows.append(
            {
                "Character": char,
                "Priority": priority(first_rank[char]),
                "First Rank": str(first_rank[char]),
                "First Word": samples[0][1],
                "Deck Word Count": str(len(samples)),
                "Sample Deck Words": "; ".join(f"{word} ({rank})" for rank, word in samples[:8]),
            }
        )
    return rows


def append_missing_chars(words: list[str], rows: list[dict[str, str]]) -> list[str]:
    chars_to_append = [row["Character"] for row in rows if row["Character"] not in set(words)]
    if not chars_to_append:
        return []

    WORD_LIST_BACKUP.write_text(WORD_LIST.read_text(encoding="utf-8-sig"), encoding="utf-8")
    WORD_LIST.write_text("\n".join(words + chars_to_append) + "\n", encoding="utf-8")
    return chars_to_append


def ranks_by_word(words: list[str]) -> dict[str, int]:
    return {word: rank for rank, word in enumerate(words, start=1)}


def load_source_rows() -> dict[str, dict[str, str]]:
    with SOURCE_TSV.open(encoding="utf-8", newline="") as handle:
        return {
            character_add.clean(row["Word"]): {key: character_add.clean(value) for key, value in row.items()}
            for row in csv.DictReader(handle, delimiter="\t")
        }


def write_added(rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "Note ID",
        "Character",
        "Pinyin",
        "Meaning",
        "Priority",
        "Frequency Rank",
        "First Deck Word",
        "First Deck Word Rank",
        "Example",
        "Example Meaning",
    ]
    with APPLIED_TSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def coverage_stats(words: list[str]) -> dict[str, int]:
    used_chars = {char for word in words for char in hanzi_chars(word)}
    single_chars = {
        word
        for word in words
        if len(hanzi_chars(word)) == 1 and "".join(hanzi_chars(word)) == word
    }
    return {
        "word_list_rows": len(words),
        "unique_hanzi_used": len(used_chars),
        "single_character_notes_in_word_list": len(single_chars),
        "used_chars_without_single_note": len(used_chars - single_chars),
    }


def write_report(
    before: dict[str, int],
    after: dict[str, int],
    missing_rows: list[dict[str, str]],
    appended_chars: list[str],
    added_rows: list[dict[str, str]],
    verification: dict[str, Any] | None,
) -> None:
    lines = [
        "# Single Character Notes Policy Report",
        "",
        "Policy: every Hanzi character used in any multi-character deck word must also exist as a single-character note.",
        "",
        "Before:",
        f"- word-list rows: {before['word_list_rows']}",
        f"- unique Hanzi used: {before['unique_hanzi_used']}",
        f"- single-character notes in word list: {before['single_character_notes_in_word_list']}",
        f"- used chars without single note: {before['used_chars_without_single_note']}",
        "",
        "Action:",
        f"- missing character rows found: {len(missing_rows)}",
        f"- characters appended to word list: {len(appended_chars)}",
        f"- notes added to Anki: {len(added_rows)}",
        "",
        "After:",
        f"- word-list rows: {after['word_list_rows']}",
        f"- unique Hanzi used: {after['unique_hanzi_used']}",
        f"- single-character notes in word list: {after['single_character_notes_in_word_list']}",
        f"- used chars without single note: {after['used_chars_without_single_note']}",
    ]
    if verification:
        lines.extend(
            [
                "",
                "Anki verification:",
                f"- live notes: {verification['notes']}",
                f"- live cards: {verification['cards']}",
                f"- proposed chars missing after add: {verification['proposed_missing_after_add']}",
                f"- blank required fields: {len(verification['blank_required_fields'])}",
            ]
        )
    lines.extend(
        [
            "",
            "Files:",
            f"- {WORD_LIST_BACKUP.name}: source word-list backup, created only when characters are appended",
            f"- {APPLIED_TSV.name}: note IDs and fields added by the latest policy run",
            f"- {SOURCE_TSV.name}: rebuilt TSV source data, when additions were needed",
        ]
    )
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    words_before = read_words()
    before = coverage_stats(words_before)
    missing_rows = missing_character_rows(words_before)

    if not missing_rows:
        write_added([])
        write_report(before, before, [], [], [], verification=None)
        print(json.dumps({**before, "missing_character_rows": 0, "notes_added": 0}, ensure_ascii=False, indent=2))
        return

    appended_chars = append_missing_chars(words_before, missing_rows)
    words_after_append = read_words()

    build_anki_chinese.main()
    source_by_word = load_source_rows()
    added_rows = character_add.add_notes(missing_rows, ranks_by_word(words_after_append), source_by_word)
    write_added(added_rows)

    setup_production_sentence_cards.main()
    verification = character_add.verify([row["Character"] for row in missing_rows])
    after = coverage_stats(read_words())
    write_report(before, after, missing_rows, appended_chars, added_rows, verification)
    print(
        json.dumps(
            {
                **after,
                "missing_character_rows": len(missing_rows),
                "appended_chars": len(appended_chars),
                "notes_added": len(added_rows),
                "anki_notes": verification["notes"],
                "anki_cards": verification["cards"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
