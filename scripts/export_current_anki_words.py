"""Read-only export of current Chinese deck membership, not a known-word list."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
QUERY = 'deck:"Default" note:"Chinese Vocabulary"'
WORDS_PATH = ROOT / 'anki/current_deck_words.txt'
METADATA_PATH = ROOT / 'anki/current_deck_words.metadata.json'


def anki(action, params):
    request = Request('http://127.0.0.1:8765',
                      data=json.dumps({'action': action, 'version': 6, 'params': params}).encode('utf-8'),
                      headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get('error'):
        raise RuntimeError(f"{action}: {result['error']}")
    return result['result']


def read_membership(call=anki):
    ids = sorted(call('findNotes', {'query': QUERY}))
    if not ids or len(ids) != len(set(ids)):
        raise ValueError('Empty deck or invalid note IDs; refusing to replace the export')
    pairs = []
    for start in range(0, len(ids), 250):
        notes = call('notesInfo', {'notes': ids[start:start + 250]})
        for note in notes:
            if note.get('modelName') != 'Chinese Vocabulary':
                raise ValueError('Unexpected note model in export')
            word = note.get('fields', {}).get('Word', {}).get('value', '').strip()
            if not word or any(c in word for c in '\r\n\t<>'):
                raise ValueError('Blank or non-plain-text Word field; inspect the deck before exporting')
            pairs.append((note['noteId'], word))
    if sorted(nid for nid, _ in pairs) != ids:
        raise ValueError('Missing or duplicate notesInfo result')
    cards = sorted(call('findCards', {'query': QUERY}))
    if not cards or len(cards) != len(set(cards)):
        raise ValueError('Empty or invalid card membership')
    return {'notes': sorted(pairs), 'cards': cards}


def export_words(*, call=anki, word_path=WORDS_PATH, metadata_path=METADATA_PATH,
                 ranked_source=ROOT / 'word list chinese.txt'):
    # Two reads detect changed membership or Word fields; schedule changes do not
    # invalidate a vocabulary-only inventory. Never change anything in Anki.
    before = read_membership(call)
    if before != read_membership(call):
        raise RuntimeError('Deck membership changed during export; retry without editing notes')
    counts = Counter(word for _, word in before['notes'])
    words = sorted(counts)
    payload = ('\n'.join(words) + '\n').encode('utf-8')
    source_bytes = ranked_source.read_bytes()
    source_text = source_bytes.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
    source_words = {w.strip() for w in source_text.splitlines() if w.strip()}
    metadata = {
        'exported_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'source': 'Live Anki collection through read-only AnkiConnect queries',
        'deck': 'Default', 'model': 'Chinese Vocabulary', 'query': QUERY,
        'scope': 'All matching notes, including new, learning, review, suspended and buried cards; Default subdecks are included if present',
        'format': 'UTF-8 without BOM; one unique Word field per line; Unicode-sorted, not frequency or study order',
        'note_count': len(before['notes']), 'card_count': len(before['cards']),
        'unique_word_count': len(words),
        'duplicate_word_note_count': sum(n - 1 for n in counts.values()),
        'duplicate_words': sorted(w for w, n in counts.items() if n > 1),
        'words_sha256': hashlib.sha256(payload).hexdigest(),
        'ranked_source_file': ranked_source.name,
        'ranked_source_sha256': hashlib.sha256(source_text.encode('utf-8')).hexdigest(),
        'ranked_source_hash_normalization': 'UTF-8 without BOM, LF line endings; stable across Git checkouts',
        'ranked_source_unique_word_count': len(source_words),
        'live_words_absent_from_ranked_source_count': len(set(words) - source_words),
        'ranked_source_words_absent_from_live_deck_count': len(source_words - set(words)),
        'read_consistency_check': 'Two matching live membership/Word-field reads',
        'privacy': 'No note/card IDs, tags, examples, scheduling state or review history exported',
        'not_a_mastery_list': True,
    }
    word_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    word_path.write_bytes(payload)
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=WORDS_PATH)
    parser.add_argument('--metadata', type=Path, default=METADATA_PATH)
    args = parser.parse_args()
    print(json.dumps(export_words(word_path=args.out, metadata_path=args.metadata), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
