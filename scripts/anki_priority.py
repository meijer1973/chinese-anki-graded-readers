from __future__ import annotations

import re
from typing import Any


PRIORITY_TAG_RE = re.compile(r"^pilot_[a-z0-9_]+_priority_(\d+)$")


def priority_from_tags(tags: list[str] | set[str] | tuple[str, ...]) -> int | None:
    values = [
        int(match.group(1))
        for tag in tags
        if (match := PRIORITY_TAG_RE.fullmatch(str(tag)))
    ]
    return min(values) if values else None


def priority_new_card_ids(
    notes: list[dict[str, Any]],
    cards_by_note: dict[int, list[dict[str, Any]]],
    *,
    active_card_ords: set[int],
) -> list[int]:
    """Return active unseen pilot cards in persistent tag-priority/template order."""
    ordered: list[tuple[int, int, int]] = []
    for note in notes:
        priority = priority_from_tags(note.get("tags", []))
        if priority is None:
            continue
        for card in cards_by_note.get(int(note["noteId"]), []):
            card_ord = int(card.get("ord", -1))
            if (
                card_ord in active_card_ords
                and int(card.get("type", -1)) == 0
                and int(card.get("queue", -1)) >= 0
            ):
                ordered.append((priority, card_ord, int(card["cardId"])))
    return [card_id for _, _, card_id in sorted(ordered)]
