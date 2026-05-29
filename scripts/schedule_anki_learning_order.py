from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import setup_production_sentence_cards as card_setup  # noqa: E402
from scripts.anki_card_distribution import (  # noqa: E402
    DISTRIBUTION_REPORT,
    LEARNING_ORDER_PLAN,
    NOTE_TYPE_SINGLE,
    NOTE_TYPE_WORD,
    WORD_LIST,
    ScheduleConfig,
    audit_distribution,
    build_and_write_learning_order_outputs,
    build_learning_order_plan,
    dump_json,
    evenly_interleave_items,
    is_single_hanzi_note,
    read_word_list,
)


PENDING_TAG = "single_character_release_pending"
ACTIVE_TAG = "single_character_release_active"
SCHEDULE_TAG = "single_character_scheduled"
ACTIVE_CARD_ORDS = {0, 2}


def chunked(values: list[int], size: int) -> Iterable[list[int]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def note_tags(note: dict[str, Any]) -> set[str]:
    return {str(tag) for tag in note.get("tags", [])}


def cards_by_note(cards: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    grouped: dict[int, list[dict[str, Any]]] = {}
    for card in cards:
        grouped.setdefault(int(card["note"]), []).append(card)
    return grouped


def is_new_card(card: dict[str, Any], *, include_suspended: bool = False) -> bool:
    if int(card.get("ord", -1)) not in ACTIVE_CARD_ORDS:
        return False
    if int(card.get("type", -1)) != 0:
        return False
    return include_suspended or int(card.get("queue", -1)) >= 0


def note_has_new_card(note: dict[str, Any], note_cards: dict[int, list[dict[str, Any]]], *, include_suspended: bool) -> bool:
    return any(is_new_card(card, include_suspended=include_suspended) for card in note_cards.get(int(note["noteId"]), []))


def note_has_reviewed_cn_to_en_card(note: dict[str, Any], note_cards: dict[int, list[dict[str, Any]]]) -> bool:
    return any(
        int(card.get("ord", -1)) in ACTIVE_CARD_ORDS and int(card.get("type", -1)) != 0
        for card in note_cards.get(int(note["noteId"]), [])
    )


def anki_add_tags(note_ids: list[int], tags: str) -> None:
    for batch in chunked(note_ids, 500):
        if batch:
            card_setup.anki("addTags", {"notes": batch, "tags": tags})


def anki_remove_tags(note_ids: list[int], tags: str) -> None:
    for batch in chunked(note_ids, 500):
        if batch:
            card_setup.anki("removeTags", {"notes": batch, "tags": tags})


def card_ids_for_words(
    words: list[str],
    notes_by_word: dict[str, dict[str, Any]],
    note_cards: dict[int, list[dict[str, Any]]],
) -> list[int]:
    normal_card_items: list[dict[str, Any]] = []
    single_card_items: list[dict[str, Any]] = []

    for learning_index, word in enumerate(words, start=1):
        note = notes_by_word.get(word)
        if not note:
            continue
        word_cards = [
            card
            for card in sorted(note_cards.get(int(note["noteId"]), []), key=lambda item: int(item.get("ord", 99)))
            if is_new_card(card, include_suspended=False)
        ]
        word_note_type = NOTE_TYPE_SINGLE if is_single_hanzi_note(word) else NOTE_TYPE_WORD
        target = single_card_items if word_note_type == NOTE_TYPE_SINGLE else normal_card_items
        for card in word_cards:
            target.append(
                {
                    "source_rank": learning_index,
                    "word": word,
                    "note_type": word_note_type,
                    "card_id": int(card["cardId"]),
                }
            )

    ordered_cards = evenly_interleave_items(normal_card_items, single_card_items)
    return [int(item["card_id"]) for item in ordered_cards]


def set_new_card_due_order(card_ids: list[int], *, starting_from: int = 0) -> None:
    actions = [
        {
            "action": "setSpecificValueOfCard",
            "params": {"card": card_id, "keys": ["due"], "newValues": [starting_from + index]},
        }
        for index, card_id in enumerate(card_ids)
    ]
    for start in range(0, len(actions), 100):
        results = card_setup.anki("multi", {"actions": actions[start : start + 100]})
        for result in results:
            if isinstance(result, dict) and result.get("error"):
                raise RuntimeError(result["error"])


def apply_learning_order_to_anki(words: list[str], config: ScheduleConfig) -> dict[str, Any]:
    notes = card_setup.load_notes()
    cards = card_setup.load_cards()
    note_cards = cards_by_note(cards)
    notes_by_word = {card_setup.note_field(note, "Word"): note for note in notes if card_setup.note_field(note, "Word")}

    cn_to_en_cards_to_unsuspend = [
        int(card["cardId"])
        for card in cards
        if int(card.get("ord", -1)) in ACTIVE_CARD_ORDS and int(card.get("queue", 0)) < 0
    ]
    for batch in chunked(cn_to_en_cards_to_unsuspend, 500):
        if batch:
            card_setup.unsuspend_cards(batch)

    pending_tag_note_ids = [int(note["noteId"]) for note in notes if PENDING_TAG in note_tags(note)]
    anki_remove_tags(pending_tag_note_ids, PENDING_TAG)

    cards_after_unsuspend = card_setup.load_cards()
    note_cards = cards_by_note(cards_after_unsuspend)

    source_words = [word for word in words if word in notes_by_word]
    source_word_set = set(source_words)
    extra_new_words = [
        card_setup.note_field(note, "Word")
        for note in notes
        if card_setup.note_field(note, "Word")
        and card_setup.note_field(note, "Word") not in source_word_set
        and note_has_new_card(note, note_cards, include_suspended=False)
    ]
    schedule_words = source_words + extra_new_words

    single_words = {
        row["Word"]
        for row in build_learning_order_plan(schedule_words, config)
        if row["Note Type"] == NOTE_TYPE_SINGLE
    }

    fresh_normal_new_words: list[str] = []
    fresh_single_new_words: list[str] = []
    started_normal_new_words: list[str] = []
    started_single_new_words: list[str] = []
    for word in schedule_words:
        note = notes_by_word[word]
        has_reviewed_cn_to_en = note_has_reviewed_cn_to_en_card(note, note_cards)
        if word in single_words:
            if note_has_new_card(note, note_cards, include_suspended=False):
                if has_reviewed_cn_to_en:
                    started_single_new_words.append(word)
                else:
                    fresh_single_new_words.append(word)
        elif note_has_new_card(note, note_cards, include_suspended=False):
            if has_reviewed_cn_to_en:
                started_normal_new_words.append(word)
            else:
                fresh_normal_new_words.append(word)

    fresh_word_set = set(fresh_normal_new_words) | set(fresh_single_new_words)
    started_word_set = set(started_normal_new_words) | set(started_single_new_words)
    fresh_pool = [word for word in schedule_words if word in fresh_word_set]
    started_pool = [word for word in schedule_words if word in started_word_set]
    fresh_plan = build_learning_order_plan(fresh_pool, config)
    started_plan = build_learning_order_plan(started_pool, config)
    live_plan = []
    for row in fresh_plan + started_plan:
        updated = dict(row)
        updated["Learning Order"] = str(len(live_plan) + 1)
        live_plan.append(updated)
    released_single_word_list = [
        row["Word"]
        for row in live_plan
        if row["Note Type"] == NOTE_TYPE_SINGLE
    ]
    released_single_words = set(released_single_word_list)
    active_live_words = [
        row["Word"]
        for row in sorted(
            live_plan,
            key=lambda item: int(item["Learning Order"]),
        )
    ]

    released_note_ids = [int(notes_by_word[word]["noteId"]) for word in released_single_words if word in notes_by_word]

    anki_add_tags(released_note_ids, f"{SCHEDULE_TAG} {ACTIVE_TAG}")

    # Reload cards after tag updates so reposition sees the current new-card queue.
    cards_after_unsuspend = card_setup.load_cards()
    note_cards_after_unsuspend = cards_by_note(cards_after_unsuspend)
    cn_to_en_new_cards_still_suspended = sum(
        1
        for card in cards_after_unsuspend
        if int(card.get("ord", -1)) in ACTIVE_CARD_ORDS
        and int(card.get("type", -1)) == 0
        and int(card.get("queue", 0)) < 0
    )
    reposition_card_ids = card_ids_for_words(active_live_words, notes_by_word, note_cards_after_unsuspend)
    repositioned_count = 0
    reposition_error = ""
    queue_order_method = ""
    if reposition_card_ids:
        try:
            card_setup.anki(
                "reposition",
                {
                    "cards": reposition_card_ids,
                    "startingFrom": 0,
                    "step": 1,
                    "randomize": False,
                    "shiftPosition": True,
                },
            )
            repositioned_count = len(reposition_card_ids)
            queue_order_method = "reposition"
        except Exception as exc:  # pragma: no cover - depends on AnkiConnect version
            try:
                set_new_card_due_order(reposition_card_ids)
                repositioned_count = len(reposition_card_ids)
                queue_order_method = "setSpecificValueOfCard:due"
                reposition_error = f"reposition unsupported; used due-field fallback ({exc})"
            except Exception as fallback_exc:  # pragma: no cover - depends on AnkiConnect version
                reposition_error = f"{exc}; fallback failed: {fallback_exc}"

    live_audit = audit_distribution(active_live_words, run_threshold=config.run_threshold, window_sizes=(config.window_size,))
    live_window = live_audit["window_distribution"].get(str(config.window_size), {})
    return {
        "new_normal_notes": len(fresh_normal_new_words) + len(started_normal_new_words),
        "new_single_character_notes": len(fresh_single_new_words) + len(started_single_new_words),
        "fresh_new_normal_notes": len(fresh_normal_new_words),
        "fresh_new_single_character_notes": len(fresh_single_new_words),
        "already_started_new_normal_notes": len(started_normal_new_words),
        "already_started_new_single_character_notes": len(started_single_new_words),
        "released_single_character_notes": len(released_single_words),
        "pending_single_character_notes": 0,
        "cn_to_en_cards_unsuspended": len(cn_to_en_cards_to_unsuspend),
        "cn_to_en_new_cards_still_suspended": cn_to_en_new_cards_still_suspended,
        "new_cards_repositioned": repositioned_count,
        "queue_order_method": queue_order_method,
        "live_longest_single_character_run": live_audit["longest_consecutive_single_character_run"]["length"],
        "live_window_max_single_character_cards": live_window.get("max_single_character_cards"),
        "first_pending_single_characters": [],
        "reposition_error": reposition_error,
    }


def run_learning_order_scheduler(
    *,
    word_list: Path = WORD_LIST,
    config: ScheduleConfig | None = None,
    apply_anki: bool = True,
    plan_path: Path = LEARNING_ORDER_PLAN,
    report_path: Path = DISTRIBUTION_REPORT,
) -> dict[str, Any]:
    config = config or ScheduleConfig()
    words = read_word_list(word_list)
    anki_result = apply_learning_order_to_anki(words, config) if apply_anki else None
    output = build_and_write_learning_order_outputs(
        words,
        config=config,
        plan_path=plan_path,
        report_path=report_path,
        anki_result=anki_result,
    )
    if anki_result is not None:
        output["anki_result"] = anki_result
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and optionally apply an interleaved Anki learning order.")
    parser.add_argument("--word-list", type=Path, default=WORD_LIST)
    parser.add_argument("--plan", type=Path, default=LEARNING_ORDER_PLAN)
    parser.add_argument("--report", type=Path, default=DISTRIBUTION_REPORT)
    parser.add_argument("--no-anki", action="store_true", help="Only write the local TSV/report; do not mutate Anki.")
    parser.add_argument("--cards-per-single", type=int, default=2)
    parser.add_argument("--max-consecutive-single", type=int, default=1)
    parser.add_argument("--window-size", type=int, default=20)
    parser.add_argument("--min-single-per-window", type=int, default=4)
    parser.add_argument("--max-single-per-window", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = ScheduleConfig(
        cards_per_single=args.cards_per_single,
        max_consecutive_single=args.max_consecutive_single,
        window_size=args.window_size,
        min_single_per_window=args.min_single_per_window,
        max_single_per_window=args.max_single_per_window,
    )
    result = run_learning_order_scheduler(
        word_list=args.word_list,
        config=config,
        apply_anki=not args.no_anki,
        plan_path=args.plan,
        report_path=args.report,
    )
    print(dump_json({"summary": result["summary"], "anki_result": result.get("anki_result")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
