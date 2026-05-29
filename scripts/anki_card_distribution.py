from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
WORD_LIST = ROOT / "word list chinese.txt"
LEARNING_ORDER_PLAN = ROOT / "anki" / "learning_order_plan.tsv"
DISTRIBUTION_REPORT = ROOT / "single_character_distribution_report.md"

DEFAULT_RUN_THRESHOLD = 5
DEFAULT_WINDOW_SIZES = (20, 50, 100)

NOTE_TYPE_SINGLE = "single_hanzi"
NOTE_TYPE_WORD = "multi_character_or_word"
STATUS_ACTIVE = "active"
STATUS_PENDING = "pending"


@dataclass(frozen=True)
class ScheduleConfig:
    cards_per_single: int = 2
    max_consecutive_single: int = 1
    window_size: int = 20
    min_single_per_window: int = 4
    max_single_per_window: int = 10
    run_threshold: int = DEFAULT_RUN_THRESHOLD

    @property
    def normal_cards_between_singles(self) -> int:
        return max(1, self.cards_per_single - 1)


def is_hanzi(char: str) -> bool:
    return "\u3400" <= char <= "\u9fff" or "\uf900" <= char <= "\ufaff"


def is_single_hanzi_note(word: str) -> bool:
    return len(word) == 1 and is_hanzi(word)


def is_multi_character_or_word_note(word: str) -> bool:
    return not is_single_hanzi_note(word)


def read_word_list(path: Path = WORD_LIST) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def note_type(word: str) -> str:
    return NOTE_TYPE_SINGLE if is_single_hanzi_note(word) else NOTE_TYPE_WORD


def _run_kind(word: str, *, single: bool) -> bool:
    return is_single_hanzi_note(word) if single else is_multi_character_or_word_note(word)


def runs(words: list[str], *, single: bool) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    start: int | None = None
    length = 0

    for index, word in enumerate(words, start=1):
        if _run_kind(word, single=single):
            if start is None:
                start = index
                length = 0
            length += 1
            continue

        if start is not None:
            found.append({"start": start, "end": index - 1, "length": length})
            start = None
            length = 0

    if start is not None:
        found.append({"start": start, "end": len(words), "length": length})
    return found


def longest_run(words: list[str], *, single: bool) -> dict[str, Any]:
    all_runs = runs(words, single=single)
    if not all_runs:
        return {"start": None, "end": None, "length": 0}
    return max(all_runs, key=lambda item: item["length"])


def runs_over_threshold(words: list[str], threshold: int, *, single: bool = True) -> list[dict[str, Any]]:
    return [run for run in runs(words, single=single) if run["length"] > threshold]


def window_distribution(words: list[str], window_sizes: Iterable[int] = DEFAULT_WINDOW_SIZES) -> dict[str, dict[str, Any]]:
    distributions: dict[str, dict[str, Any]] = {}
    single_flags = [1 if is_single_hanzi_note(word) else 0 for word in words]

    for window_size in window_sizes:
        if window_size <= 0:
            raise ValueError("window sizes must be positive")

        key = str(window_size)
        if len(words) < window_size:
            distributions[key] = {
                "window_size": window_size,
                "window_count": 0,
                "min_single_character_cards": None,
                "max_single_character_cards": None,
                "average_single_character_cards": None,
                "histogram": {},
                "max_windows": [],
            }
            continue

        counts: list[int] = []
        current = sum(single_flags[:window_size])
        counts.append(current)
        for index in range(window_size, len(single_flags)):
            current += single_flags[index] - single_flags[index - window_size]
            counts.append(current)

        max_count = max(counts)
        histogram: dict[str, int] = {}
        for count in counts:
            histogram[str(count)] = histogram.get(str(count), 0) + 1

        max_windows = [
            {"start": index + 1, "end": index + window_size, "single_character_cards": count}
            for index, count in enumerate(counts)
            if count == max_count
        ][:20]

        distributions[key] = {
            "window_size": window_size,
            "window_count": len(counts),
            "min_single_character_cards": min(counts),
            "max_single_character_cards": max_count,
            "average_single_character_cards": round(sum(counts) / len(counts), 2),
            "histogram": histogram,
            "max_windows": max_windows,
        }

    return distributions


def audit_distribution(
    words: list[str],
    *,
    run_threshold: int = DEFAULT_RUN_THRESHOLD,
    window_sizes: Iterable[int] = DEFAULT_WINDOW_SIZES,
) -> dict[str, Any]:
    total = len(words)
    single_count = sum(1 for word in words if is_single_hanzi_note(word))
    multi_count = total - single_count

    return {
        "total_rows": total,
        "single_character_rows": single_count,
        "single_character_percent": round((single_count / total * 100) if total else 0.0, 2),
        "multi_character_or_word_rows": multi_count,
        "multi_character_or_word_percent": round((multi_count / total * 100) if total else 0.0, 2),
        "longest_consecutive_single_character_run": longest_run(words, single=True),
        "longest_consecutive_multi_character_or_word_run": longest_run(words, single=False),
        "single_character_runs_over_threshold": runs_over_threshold(words, run_threshold, single=True),
        "window_distribution": window_distribution(words, window_sizes),
    }


def audit_passes(
    audit: dict[str, Any],
    *,
    max_single_run: int = 1,
    window_size: int = 20,
    max_single_per_window: int = 10,
) -> bool:
    longest = audit["longest_consecutive_single_character_run"]["length"]
    window = audit["window_distribution"].get(str(window_size), {})
    window_max = window.get("max_single_character_cards")
    return longest <= max_single_run and (window_max is None or window_max <= max_single_per_window)


def _source_items(words: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "source_rank": index,
            "word": word,
            "note_type": note_type(word),
        }
        for index, word in enumerate(words, start=1)
    ]


def evenly_interleave_items(normal_items: list[dict[str, Any]], single_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total = len(normal_items) + len(single_items)
    if not normal_items:
        return list(single_items)
    if not single_items:
        return list(normal_items)

    ordered: list[dict[str, Any]] = []
    normal_index = 0
    single_index = 0

    for position in range(1, total + 1):
        normal_remaining = len(normal_items) - normal_index
        single_remaining = len(single_items) - single_index
        if normal_remaining <= 0:
            ordered.append(single_items[single_index])
            single_index += 1
            continue
        if single_remaining <= 0:
            ordered.append(normal_items[normal_index])
            normal_index += 1
            continue

        single_deficit = len(single_items) * position / total - single_index
        normal_deficit = len(normal_items) * position / total - normal_index
        should_place_single = single_deficit > normal_deficit
        previous_was_single = bool(ordered and ordered[-1]["note_type"] == NOTE_TYPE_SINGLE)
        can_avoid_single_run = single_remaining <= normal_remaining + 1

        if should_place_single and not (previous_was_single and can_avoid_single_run):
            ordered.append(single_items[single_index])
            single_index += 1
        else:
            ordered.append(normal_items[normal_index])
            normal_index += 1

    return ordered


def build_learning_order_plan(words: list[str], config: ScheduleConfig | None = None) -> list[dict[str, str]]:
    config = config or ScheduleConfig()
    items = _source_items(words)
    normal_items = [item for item in items if item["note_type"] == NOTE_TYPE_WORD]
    single_items = [item for item in items if item["note_type"] == NOTE_TYPE_SINGLE]

    active_order = evenly_interleave_items(normal_items, single_items)

    rows: list[dict[str, str]] = []
    for learning_order, item in enumerate(active_order, start=1):
        rows.append(
            {
                "Learning Order": str(learning_order),
                "Source Rank": str(item["source_rank"]),
                "Word": item["word"],
                "Note Type": item["note_type"],
                "Scheduling Status": STATUS_ACTIVE,
                "Reason": "normal_word" if item["note_type"] == NOTE_TYPE_WORD else "interleaved_single_hanzi",
                "Frequency Rank Preserved": str(item["source_rank"]),
            }
        )

    return rows


def active_words_from_plan(plan_rows: list[dict[str, str]]) -> list[str]:
    active_rows = [row for row in plan_rows if row["Scheduling Status"] == STATUS_ACTIVE]
    active_rows.sort(key=lambda row: int(row["Learning Order"]))
    return [row["Word"] for row in active_rows]


def plan_summary(plan_rows: list[dict[str, str]]) -> dict[str, Any]:
    active = [row for row in plan_rows if row["Scheduling Status"] == STATUS_ACTIVE]
    pending = [row for row in plan_rows if row["Scheduling Status"] == STATUS_PENDING]
    active_single = [row for row in active if row["Note Type"] == NOTE_TYPE_SINGLE]
    pending_single = [row for row in pending if row["Note Type"] == NOTE_TYPE_SINGLE]
    active_word = [row for row in active if row["Note Type"] == NOTE_TYPE_WORD]

    return {
        "total_rows": len(plan_rows),
        "active_rows": len(active),
        "pending_rows": len(pending),
        "active_multi_character_or_word_rows": len(active_word),
        "active_single_character_rows": len(active_single),
        "pending_single_character_rows": len(pending_single),
        "first_pending_single_characters": [row["Word"] for row in pending_single[:50]],
    }


def audit_learning_plan(
    plan_rows: list[dict[str, str]],
    *,
    run_threshold: int = DEFAULT_RUN_THRESHOLD,
    window_sizes: Iterable[int] = DEFAULT_WINDOW_SIZES,
) -> dict[str, Any]:
    return audit_distribution(active_words_from_plan(plan_rows), run_threshold=run_threshold, window_sizes=window_sizes)


def write_learning_order_plan(plan_rows: list[dict[str, str]], path: Path = LEARNING_ORDER_PLAN) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "Learning Order",
        "Source Rank",
        "Word",
        "Note Type",
        "Scheduling Status",
        "Reason",
        "Frequency Rank Preserved",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(plan_rows)


def _format_run(run: dict[str, Any]) -> str:
    if not run["length"]:
        return "none"
    return f"{run['length']} rows ({run['start']}-{run['end']})"


def _window_line(audit: dict[str, Any], window_size: int) -> str:
    window = audit["window_distribution"].get(str(window_size), {})
    if not window or window["window_count"] == 0:
        return f"- {window_size}: not enough rows for a full window"
    return (
        f"- {window_size}: min {window['min_single_character_cards']}, "
        f"max {window['max_single_character_cards']}, "
        f"avg {window['average_single_character_cards']} single-character rows"
    )


def markdown_audit_report(audit: dict[str, Any], *, title: str = "Anki Card Distribution Audit") -> str:
    lines = [
        f"# {title}",
        "",
        f"Total rows: {audit['total_rows']}",
        f"Single-character rows: {audit['single_character_rows']} ({audit['single_character_percent']}%)",
        f"Multi-character/word rows: {audit['multi_character_or_word_rows']} ({audit['multi_character_or_word_percent']}%)",
        f"Longest single-character run: {_format_run(audit['longest_consecutive_single_character_run'])}",
        f"Longest multi-character/word run: {_format_run(audit['longest_consecutive_multi_character_or_word_run'])}",
        "",
        "Window distribution:",
    ]
    for window_size in DEFAULT_WINDOW_SIZES:
        lines.append(_window_line(audit, window_size))

    long_runs = audit["single_character_runs_over_threshold"]
    lines.extend(["", f"Single-character runs over threshold: {len(long_runs)}"])
    for run in long_runs[:50]:
        lines.append(f"- {run['start']}-{run['end']} ({run['length']})")
    if len(long_runs) > 50:
        lines.append(f"- ... {len(long_runs) - 50} more")
    return "\n".join(lines).rstrip() + "\n"


def markdown_distribution_report(
    source_audit: dict[str, Any],
    active_audit: dict[str, Any],
    summary: dict[str, Any],
    config: ScheduleConfig,
    *,
    anki_result: dict[str, Any] | None = None,
    plan_path: Path = LEARNING_ORDER_PLAN,
) -> str:
    lines = [
        "# Single Character Distribution Report",
        "",
        "Frequency rank remains the source-list row number. Learning order is generated separately.",
        "",
        "Scheduler configuration:",
        "- all Chinese-to-English new cards stay unsuspended",
        "- single-character and multi-character notes are interleaved as evenly as the available new-card pool allows",
        f"- preferred max consecutive single-character notes: {config.max_consecutive_single}",
        f"- 20-row target window: up to {config.max_single_per_window} single-character notes when supply allows",
        "",
        "Raw source order:",
        f"- total rows: {source_audit['total_rows']}",
        f"- single-character rows: {source_audit['single_character_rows']} ({source_audit['single_character_percent']}%)",
        f"- longest single-character run: {_format_run(source_audit['longest_consecutive_single_character_run'])}",
        _window_line(source_audit, 20),
        "",
        "Active learning order:",
        f"- active rows: {summary['active_rows']}",
        f"- active single-character rows: {summary['active_single_character_rows']}",
        f"- pending single-character rows: {summary['pending_single_character_rows']}",
        f"- longest single-character run: {_format_run(active_audit['longest_consecutive_single_character_run'])}",
        _window_line(active_audit, 20),
        "",
        "Files:",
        f"- {plan_path.as_posix()}: generated learning-order plan",
    ]

    if anki_result is not None:
        lines.extend(
            [
                "",
                "Live Anki application:",
                f"- new normal notes available: {anki_result.get('new_normal_notes', 0)}",
                f"- new single-character notes available: {anki_result.get('new_single_character_notes', 0)}",
                f"- fresh new normal notes first: {anki_result.get('fresh_new_normal_notes', 0)}",
                f"- fresh new single-character notes first: {anki_result.get('fresh_new_single_character_notes', 0)}",
                f"- already-started notes moved later: {anki_result.get('already_started_new_normal_notes', 0) + anki_result.get('already_started_new_single_character_notes', 0)}",
                f"- single-character notes included in active schedule: {anki_result.get('released_single_character_notes', 0)}",
                f"- Chinese-to-English cards unsuspended this run: {anki_result.get('cn_to_en_cards_unsuspended', 0)}",
                f"- suspended Chinese-to-English new cards remaining: {anki_result.get('cn_to_en_new_cards_still_suspended', 0)}",
                f"- new cards repositioned: {anki_result.get('new_cards_repositioned', 0)}",
                f"- queue-order method: {anki_result.get('queue_order_method', 'n/a') or 'n/a'}",
                f"- active new-note longest single-character run: {anki_result.get('live_longest_single_character_run', 0)}",
                f"- active {config.window_size}-note max single-character count: {anki_result.get('live_window_max_single_character_cards', 'n/a')}",
            ]
        )
        if anki_result.get("reposition_error"):
            lines.append(f"- reposition warning: {anki_result['reposition_error']}")

    return "\n".join(lines).rstrip() + "\n"


def build_and_write_learning_order_outputs(
    words: list[str],
    *,
    config: ScheduleConfig | None = None,
    plan_path: Path = LEARNING_ORDER_PLAN,
    report_path: Path = DISTRIBUTION_REPORT,
    anki_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = config or ScheduleConfig()
    source_audit = audit_distribution(words, run_threshold=config.run_threshold)
    plan_rows = build_learning_order_plan(words, config)
    active_audit = audit_learning_plan(plan_rows, run_threshold=config.run_threshold)
    summary = plan_summary(plan_rows)

    write_learning_order_plan(plan_rows, plan_path)
    report_path.write_text(
        markdown_distribution_report(source_audit, active_audit, summary, config, anki_result=anki_result, plan_path=plan_path),
        encoding="utf-8",
    )

    return {
        "source_audit": source_audit,
        "active_audit": active_audit,
        "summary": summary,
        "plan_path": str(plan_path),
        "report_path": str(report_path),
    }


def dump_json(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)
