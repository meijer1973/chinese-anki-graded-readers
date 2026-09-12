"""Reviewed original examples for all 42 approved First Frost characters."""
import json
from pathlib import Path

MANIFEST = Path(__file__).resolve().parents[2] / 'anki/first_frost/character_pilot.json'


def load_characters():
    rows = json.loads(MANIFEST.read_text(encoding='utf-8'))['notes']
    words = [r['Word'] for r in rows]
    if len(words) != 42 or len(set(words)) != 42 or any(len(w) != 1 for w in words):
        raise ValueError('Expected 42 distinct single-character targets')
    for row in rows:
        if row['Word'] not in row['Example']:
            raise ValueError(f"Missing target in example: {row['Word']}")
        if not all(row[k] for k in ('Example', 'Example Pinyin', 'Example Meaning', 'Source')):
            raise ValueError(f"Incomplete example: {row['Word']}")
    return rows


def install_character_overrides(examples, pinyin):
    for row in load_characters():
        examples[row['Word']] = (row['Example'], row['Example Meaning'])
        pinyin[row['Example']] = row['Example Pinyin']
