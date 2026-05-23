from __future__ import annotations

import csv
import gzip
import html
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
CEDICT_GZ = ROOT / "data" / "cedict_ts.u8.gz"
FALLBACK_TSV = ROOT / "anki_chinese_review.tsv"

OUTPUT_TSV = ROOT / "meaning_field_suggestions.tsv"
SUMMARY_MD = ROOT / "meaning_field_suggestions_summary.md"

ANKI_CONNECT_URL = "http://127.0.0.1:8765"
ANKI_QUERY = "deck:Default"

TAIWAN_NOISE_RE = re.compile(
    r"\(Tw\)|\bTw\b|Taiwan pr\.|Taiwanese|Taiwan variant|southeast Taiwan",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class CedictEntry:
    pinyin: str
    definitions: tuple[str, ...]


@dataclass(frozen=True)
class NoteRow:
    note_id: str
    word: str
    pinyin: str
    meaning: str
    source: str


def clean_space(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<br\s*/?>", "; ", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    value = value.replace("\t", " ")
    return re.sub(r"\s+", " ", value).strip()


def anki_connect(action: str, params: dict[str, Any] | None = None) -> Any:
    payload = {"action": action, "version": 6}
    if params:
        payload["params"] = params

    request = Request(
        ANKI_CONNECT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=20) as response:
        data = json.loads(response.read().decode("utf-8"))

    if data.get("error"):
        raise RuntimeError(data["error"])
    return data.get("result")


def field_by_name_or_order(fields: dict[str, Any], names: tuple[str, ...], order: int) -> str:
    for name in names:
        if name in fields:
            return clean_space(fields[name].get("value", ""))

    for field in fields.values():
        if field.get("order") == order:
            return clean_space(field.get("value", ""))
    return ""


def load_notes_from_anki() -> list[NoteRow]:
    note_ids = anki_connect("findNotes", {"query": ANKI_QUERY})
    rows: list[NoteRow] = []

    for start in range(0, len(note_ids), 250):
        batch = note_ids[start : start + 250]
        for note in anki_connect("notesInfo", {"notes": batch}):
            fields = note.get("fields", {})
            rows.append(
                NoteRow(
                    note_id=str(note.get("noteId", "")),
                    word=field_by_name_or_order(fields, ("Word", "Front"), 0),
                    pinyin=field_by_name_or_order(fields, ("Pinyin", "Back"), 1),
                    meaning=field_by_name_or_order(fields, ("Meaning", "Add Reverse"), 2),
                    source="anki",
                )
            )

    rows.sort(key=lambda row: row.note_id)
    return rows


def load_notes_from_tsv() -> list[NoteRow]:
    rows: list[NoteRow] = []
    with FALLBACK_TSV.open(encoding="utf-8", newline="") as handle:
        for index, row in enumerate(csv.DictReader(handle, delimiter="\t"), start=1):
            rows.append(
                NoteRow(
                    note_id=f"tsv-{index}",
                    word=clean_space(row["Word"]),
                    pinyin=clean_space(row["Pinyin"]),
                    meaning=clean_space(row["Meaning"]),
                    source="tsv",
                )
            )
    return rows


def load_notes() -> list[NoteRow]:
    try:
        rows = load_notes_from_anki()
        if rows:
            return rows
    except (OSError, RuntimeError, URLError):
        pass
    return load_notes_from_tsv()


def parse_cedict() -> dict[str, list[CedictEntry]]:
    entries: dict[str, list[CedictEntry]] = defaultdict(list)
    pattern = re.compile(r"^(\S+)\s+(\S+)\s+\[(.+?)\]\s+/(.*)/$")

    with gzip.open(CEDICT_GZ, "rt", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            match = pattern.match(line)
            if not match:
                continue

            simplified = match.group(2)
            pinyin = clean_space(match.group(3)).replace("u:", "ü")
            definitions = tuple(
                clean_space(definition)
                for definition in match.group(4).split("/")
                if clean_space(definition)
            )
            if definitions:
                entries[simplified].append(CedictEntry(pinyin, definitions))

    return entries


def split_readings(pinyin: str) -> list[str]:
    readings = [part.strip() for part in pinyin.split("/") if part.strip()]
    return readings or ([pinyin.strip()] if pinyin.strip() else [])


def normalize_definition(definition: str) -> str:
    definition = clean_space(definition)
    definition = re.sub(r"\(as in [^)]*\)", "", definition)
    definition = re.sub(r"\(Note: [^)]*\)", "", definition)
    definition = re.sub(r"\(CL:[^)]*\)", "", definition)
    definition = re.sub(r"\(Taiwan pr\. \[[^\]]+\]\)", "", definition)
    definition = re.sub(r"\bTaiwan pr\. \[[^\]]+\]", "", definition)
    definition = re.sub(r"\bCL:[^;]+", "", definition)
    definition = re.sub(r"\s+", " ", definition).strip(" ;")
    return definition


def surname_definition(definition: str) -> bool:
    return bool(re.search(r"\bsurname\b", definition, flags=re.IGNORECASE))


def taiwan_specific_definition(definition: str) -> bool:
    lowered = definition.strip().lower()
    return lowered.startswith("(tw)") or lowered.startswith("tw ") or lowered.startswith("taiwanese ")


def low_value_definition(definition: str) -> bool:
    lowered = definition.lower()
    prefixes = (
        "variant of ",
        "old variant of ",
        "erhua variant of ",
        "see ",
        "see also ",
        "also pr. ",
        "abbr. for ",
        "short for ",
        "classifier for ",
        "cl:",
    )
    return (
        lowered.startswith(prefixes)
        or surname_definition(definition)
        or taiwan_specific_definition(definition)
    )


def choose_definitions(definitions: tuple[str, ...], max_items: int) -> list[str]:
    chosen: list[str] = []
    fallback: list[str] = []

    for raw_definition in definitions:
        definition = normalize_definition(raw_definition)
        if not definition:
            continue
        if definition not in fallback:
            fallback.append(definition)
        if low_value_definition(definition):
            continue
        if definition not in chosen:
            chosen.append(definition)

    chosen = chosen or fallback
    return chosen[:max_items]


def grouped_entries(entries: list[CedictEntry]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = defaultdict(list)

    for entry in entries:
        for raw_definition in entry.definitions:
            definition = normalize_definition(raw_definition)
            if not definition:
                continue
            if low_value_definition(definition):
                continue
            if definition not in grouped[entry.pinyin]:
                grouped[entry.pinyin].append(definition)

    return {reading: definitions[:3] for reading, definitions in grouped.items()}


def concise_join(parts: list[str], max_chars: int) -> str:
    output: list[str] = []
    for part in parts:
        if not output and len(part) > max_chars:
            return part[:max_chars].rstrip(" ;")
        candidate = "; ".join(output + [part])
        if output and len(candidate) > max_chars:
            break
        output.append(part)
    return "; ".join(output) if output else (parts[0][:max_chars].rstrip(" ;") if parts else "")


def reading_order(note: NoteRow, grouped: dict[str, list[str]]) -> list[str]:
    ordered: list[str] = []
    for reading in split_readings(note.pinyin):
        if reading in grouped and reading not in ordered:
            ordered.append(reading)
    ordered.extend(reading for reading in grouped if reading not in ordered)
    return ordered


def concise_multi_reading_join(pieces: list[str], max_chars: int = 180) -> str:
    output: list[str] = []
    for piece in pieces:
        candidate = " | ".join(output + [piece])
        if output and len(candidate) > max_chars:
            break
        output.append(piece)
    return " | ".join(output) if output else (pieces[0][:max_chars].rstrip(" |;") if pieces else "")


def suggest_meaning(note: NoteRow, entries: list[CedictEntry]) -> str:
    if not entries:
        return note.meaning

    grouped = grouped_entries(entries)
    readings = reading_order(note, grouped)
    if not readings:
        return note.meaning

    if len(readings) > 1:
        pieces: list[str] = []
        for reading in readings:
            definitions = grouped[reading]
            definitions_text = concise_join(definitions, max_chars=70)
            if definitions_text:
                pieces.append(f"{reading}: {definitions_text}")
        return concise_multi_reading_join(pieces)

    definitions = grouped[readings[0]]
    return concise_join(definitions, max_chars=120)


def issue_list(note: NoteRow, entries: list[CedictEntry]) -> list[str]:
    issues: list[str] = []
    cedict_readings = {entry.pinyin for entry in entries}
    field_readings = set(split_readings(note.pinyin))
    has_multiple_readings = len(cedict_readings) > 1 or len(field_readings) > 1

    if len(note.meaning) >= 180:
        issues.append("very_long")
    elif len(note.meaning) >= 130:
        issues.append("long")
    if len(note.meaning) >= 255:
        issues.append("likely_truncated")
    if note.meaning.count(";") >= 6:
        issues.append("too_many_senses")
    if re.search(r"\bsurname\b", note.meaning, flags=re.IGNORECASE):
        issues.append("surname_noise")
    if TAIWAN_NOISE_RE.search(note.meaning):
        issues.append("taiwan_noise")
    if len(note.meaning) >= 130 and re.search(r"\b(as in|Note:|CL:|bound form|literary)\b", note.meaning):
        issues.append("dictionary_noise")
    if "&" in note.meaning or "&#" in note.meaning:
        issues.append("html_entities")
    if has_multiple_readings and issues:
        issues.insert(0, "pronunciation_specific_meanings")

    return issues


def priority_for(issues: list[str]) -> str:
    if "likely_truncated" in issues:
        return "high"
    if "pronunciation_specific_meanings" in issues and ("very_long" in issues or "dictionary_noise" in issues):
        return "high"
    if "pronunciation_specific_meanings" in issues or "very_long" in issues:
        return "medium"
    return "low"


def meaningful_change(current: str, suggested: str) -> bool:
    normalize = lambda value: re.sub(r"\W+", "", value).lower()
    return normalize(current) != normalize(suggested)


def build_suggestions() -> list[dict[str, str]]:
    notes = load_notes()
    entries_by_word = parse_cedict()
    suggestions: list[dict[str, str]] = []

    for note in notes:
        entries = entries_by_word.get(note.word, [])
        issues = issue_list(note, entries)
        if not issues:
            continue

        suggested = suggest_meaning(note, entries)
        if not suggested or not meaningful_change(note.meaning, suggested):
            continue

        suggestions.append(
            {
                "Note ID": note.note_id,
                "Word": note.word,
                "Current Pinyin": note.pinyin,
                "Current Meaning": note.meaning,
                "Issues": ", ".join(issues),
                "Priority": priority_for(issues),
                "Suggested Meaning": suggested,
                "Source": note.source,
            }
        )

    priority_order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(
        key=lambda row: (
            priority_order.get(row["Priority"], 9),
            -len(row["Current Meaning"]),
            row["Word"],
        )
    )
    return suggestions


def write_outputs(suggestions: list[dict[str, str]]) -> None:
    fieldnames = [
        "Note ID",
        "Word",
        "Current Pinyin",
        "Current Meaning",
        "Issues",
        "Priority",
        "Suggested Meaning",
        "Source",
    ]

    with OUTPUT_TSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(suggestions)

    counts: dict[str, int] = defaultdict(int)
    issue_counts: dict[str, int] = defaultdict(int)
    for row in suggestions:
        counts[row["Priority"]] += 1
        for issue in row["Issues"].split(", "):
            issue_counts[issue] += 1

    top_rows = suggestions[:30]
    lines = [
        "# Meaning Field Suggestions",
        "",
        "This is a read-only review list. No Anki notes were edited.",
        "",
        f"Total suggestions: {len(suggestions)}",
        "",
        "Priority counts:",
        f"- high: {counts['high']}",
        f"- medium: {counts['medium']}",
        f"- low: {counts['low']}",
        "",
        "Issue counts:",
    ]
    for issue, count in sorted(issue_counts.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {issue}: {count}")

    lines.extend(["", "Top suggestions:", ""])
    for row in top_rows:
        lines.append(f"## {row['Word']} ({row['Current Pinyin']})")
        lines.append(f"- Priority: {row['Priority']}")
        lines.append(f"- Issues: {row['Issues']}")
        lines.append(f"- Current: {row['Current Meaning']}")
        lines.append(f"- Suggested: {row['Suggested Meaning']}")
        lines.append("")

    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8-sig")


def main() -> None:
    suggestions = build_suggestions()
    write_outputs(suggestions)
    print(f"Wrote {len(suggestions)} suggestions to {OUTPUT_TSV.name}")
    print(f"Wrote summary to {SUMMARY_MD.name}")


if __name__ == "__main__":
    main()
