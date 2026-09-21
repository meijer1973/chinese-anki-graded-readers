"""Conservative card-level classification shared by Anki workflows."""
from __future__ import annotations

import unicodedata
from html.parser import HTMLParser


def in_deck_scope(name: str, parent: str = "Default") -> bool:
    return name == parent or name.startswith(parent + "::")


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self.hidden += 1
        elif tag == "br":
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def target_text(value: str) -> str:
    parser = _VisibleText()
    parser.feed(value)
    return "".join(parser.parts).strip()


def is_single_han(value: str) -> bool:
    return len(value) == 1 and unicodedata.name(value, "").startswith(
        ("CJK UNIFIED IDEOGRAPH-", "CJK COMPATIBILITY IDEOGRAPH-")
    )


def classify(model: str, template: dict, fields: dict[str, str]) -> tuple[str, str]:
    """Return single/sentence/keep/ambiguous, without modifying any field."""
    if model != "Chinese Vocabulary":
        return "ambiguous", "Unreviewed note model"
    front = template.get("qfmt", "")
    if template.get("name") == "Sentence Recognition" and "{{Example}}" in front and "{{Word}}" not in front:
        if target_text(fields.get("Example", "")) and fields.get("Sentence Card", "").strip():
            return "sentence", "Sentence Recognition tests the Example field"
        return "ambiguous", "Sentence template has missing/disabled sentence content"
    if template.get("name") != "Word Recognition" or "{{Word}}" not in front or "{{Example}}" in front:
        return "ambiguous", "Unreviewed or mixed learning target on the front"
    word = target_text(fields.get("Word", ""))
    if is_single_han(word):
        return "single", "Word Recognition tests exactly one Han character"
    if len(word) > 1 and all(is_single_han(c) for c in word):
        return "keep", "Word Recognition tests multiple Han characters"
    return "ambiguous", "Headword contains annotations, alternatives, or a non-Han target"
