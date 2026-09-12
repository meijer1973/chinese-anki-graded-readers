"""Audit singleton recognition cards; apply only explicit, eligible word-card IDs.

Study-state artifacts stay under ignored local_results. No new notes, templates,
cards, ranks, daily limits, or due positions are created or changed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.first_frost.character_content import load_characters  # noqa: E402

MODEL = 'Chinese Vocabulary'
TAGS = {'reading::first_frost', 'pilot::characters'}
EXAMPLE_FIELDS = ('Example', 'Example Pinyin', 'Example Meaning')
OUT = ROOT / 'anki/first_frost/local_results'
RESERVES = list('抬盯顺微低顿显忍毫缓勾僵挪臂腰喉腔似刻轻')
GAPS = list('沉默眉忽瞬侧瞥垂愣抿眸睫')


def call(action, **params):
    request = Request('http://127.0.0.1:8765',
                      data=json.dumps({'action': action, 'version': 6, 'params': params}).encode(),
                      headers={'Content-Type': 'application/json'})
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get('error'):
        raise RuntimeError(f"{action}: {result['error']}")
    return result['result']


def batch_info(action, key, ids):
    return [item for start in range(0, len(ids), 400)
            for item in call(action, **{key: ids[start:start + 400]})]


def field(note, name):
    return note['fields'][name]['value']


def snapshot(deck):
    templates = call('modelTemplates', modelName=MODEL)
    if 'Word Recognition' not in templates or '{{Word}}' not in templates['Word Recognition']['Front']:
        raise RuntimeError('Word Recognition must have a Chinese Word front')
    if '{{Example}}' in templates['Word Recognition']['Front']:
        raise RuntimeError('Unexpected sentence on Word Recognition front')
    # Model-wide lookup detects duplicate Word fields even in another deck.
    notes = batch_info('notesInfo', 'notes', call('findNotes', query=f'note:"{MODEL}"'))
    # Card-state coverage includes unrelated decks, without copying their note fields.
    cards = batch_info('cardsInfo', 'cards', call('findCards', query=''))
    by_word = defaultdict(list)
    for note in notes:
        by_word[field(note, 'Word').strip()].append(note)
    return {'templates': templates, 'config': call('getDeckConfig', deck=deck),
            'notes': notes, 'cards': cards, 'by_word': dict(by_word)}


def card_state(card):
    # These change when note text renders; they are not scheduler state.
    return {k: v for k, v in card.items() if k not in {'question', 'answer', 'fields'}}


def merge_source(old, addition):
    return old if addition in old else (old + ' | ' if old else '') + addition


def select(state, requested, deck, known=()):
    grouped = defaultdict(list)
    for card in state['cards']:
        grouped[card['note']].append(card)
    names = list(state['templates'])
    word_ord = names.index('Word Recognition')
    results = []
    for word in requested:
        notes = state['by_word'].get(word, [])
        item = {'word': word, 'note_count': len(notes), 'status': 'missing'}
        if word in known:
            item['status'] = 'user-known'
        elif len(notes) > 1:
            item['status'] = 'duplicate-conflict'
        elif notes:
            note = notes[0]
            cards = grouped[note['noteId']]
            word_cards = [c for c in cards if c['ord'] == word_ord]
            item.update(note_id=note['noteId'], cards=[{
                'id': c['cardId'], 'template': names[c['ord']], 'queue': c['queue'],
                'type': c['type'], 'reps': c['reps'], 'lapses': c['lapses'], 'due': c['due']
            } for c in cards])
            if len(word_cards) != 1:
                item['status'] = 'card-conflict'
            else:
                card = word_cards[0]
                item['card_id'] = card['cardId']
                if card['deckName'] != deck:
                    item['status'] = 'deck-conflict'
                elif 'leech' in note['tags'] or card['lapses'] >= 8:
                    item['status'] = 'leech-needs-review'
                elif card['queue'] != -1:
                    item['status'] = 'buried' if card['queue'] < -1 else 'already-active'
                elif card['reps'] or card['type'] != 0:
                    item['status'] = 'previously-studied-needs-review'
                else:
                    item['status'] = 'eligible'
        results.append(item)
    return results


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def audit(state, frequencies, deck, out):
    with frequencies.open(encoding='utf-8-sig', newline='') as handle:
        counts = {r['Word']: r for r in csv.DictReader(handle, delimiter='\t')}
    notes = {n['noteId']: n for n in state['notes']}
    names = list(state['templates'])
    rows = []
    for card in state['cards']:
        note = notes.get(card['note'])
        if not note or card['queue'] != -1 or card['deckName'] != deck:
            continue
        word = field(note, 'Word').strip()
        if (len(word) != 1 or word not in counts or int(counts[word]['Book Count']) <= 0
                or names[card['ord']] not in {'Word Recognition', 'Sentence Recognition'}):
            continue
        rows.append({**counts[word], 'Live Suspension State': 'suspended (observed queue -1)',
                     'Current Source Rank': field(note, 'Frequency Rank'),
                     'Template': names[card['ord']], 'Note ID': note['noteId'],
                     'Card ID': card['cardId'], 'Queue': card['queue'], 'Reps': card['reps'],
                     'Lapses': card['lapses'], 'Current Example': field(note, 'Example'),
                     'Current Pinyin': field(note, 'Pinyin'), 'Current Meaning': field(note, 'Meaning')})
    rows.sort(key=lambda r: (-int(r['Book Count']), r['Word'], r['Template']))
    out.mkdir(parents=True, exist_ok=True)
    if rows:
        with (out / 'suspended_character_cards_ranked.tsv').open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), delimiter='\t')
            writer.writeheader()
            writer.writerows(rows)
    return {'frequency_rows': len(counts),
            'characters_occurring_in_book': sum(int(r['Book Count']) > 0 for r in counts.values()),
            'supplied_book_count_sum': sum(int(r['Book Count']) for r in counts.values()),
            'frequency_sha256': hashlib.sha256(frequencies.read_bytes()).hexdigest(),
            'suspended_word_recognition': sum(r['Template'] == 'Word Recognition' for r in rows),
            'suspended_sentence_recognition': sum(r['Template'] == 'Sentence Recognition' for r in rows),
            'reserves': select(state, RESERVES, deck), 'supplemental': select(state, GAPS, deck),
            'duplicates': {w: [n['noteId'] for n in ns] for w, ns in state['by_word'].items() if len(w) == 1 and len(ns) > 1}}


def verify(before, after, selected, content):
    target_ids = {r['note_id']: r['word'] for r in selected}
    changed_cards = {r['card_id'] for r in selected}
    a_notes = {n['noteId']: n for n in after['notes']}
    a_cards = {c['cardId']: c for c in after['cards']}
    errors = []
    if before['templates'] != after['templates'] or before['config'] != after['config']:
        errors.append('Model templates or daily-limit configuration changed')
    if set(a_notes) != {n['noteId'] for n in before['notes']}:
        errors.append('Note membership changed')
    if set(a_cards) != {c['cardId'] for c in before['cards']}:
        errors.append('Card membership changed')
    for old in before['notes']:
        new = a_notes.get(old['noteId'])
        if not new:
            continue
        if old['noteId'] not in target_ids:
            if old != new:
                errors.append(f"Unrelated note changed: {old['noteId']}")
            continue
        row = content[target_ids[old['noteId']]]
        expected = {**{k: field(old, k) for k in old['fields']},
                    **{k: row[k] for k in EXAMPLE_FIELDS},
                    'Source': merge_source(field(old, 'Source'), row['Source'])}
        if expected != {k: field(new, k) for k in new['fields']}:
            errors.append(f"Note field mismatch: {row['Word']}")
        if set(new['tags']) != set(old['tags']) | TAGS:
            errors.append(f"Tag mismatch: {row['Word']}")
    for old in before['cards']:
        current = a_cards.get(old['cardId'])
        if not current:
            continue
        expected = card_state(old)
        if old['cardId'] in changed_cards:
            # All approved cards in this cohort are truly new.
            expected['queue'] = 0
            # Anki updates its modification timestamp when suspension changes.
            # Keep checking every scheduling field and unrelated card timestamp.
            if 'mod' in expected:
                if current['mod'] < expected['mod']:
                    errors.append(f"Card modification timestamp went backwards: {old['cardId']}")
                expected['mod'] = current['mod']
        if expected != card_state(current):
            errors.append(f"Unexpected card-state change: {old['cardId']}")
        if old['cardId'] in changed_cards:
            row = content[target_ids[old['note']]]
            if any(row[k] not in unescape(current['answer']) for k in EXAMPLE_FIELDS):
                errors.append(f"Rendered word-card example mismatch: {row['Word']}")
    return {'status': 'PASS' if not errors else 'ERROR', 'errors': errors,
            'all_cards_state_checked': len(before['cards']), 'all_chinese_notes_checked': len(before['notes']),
            'selected_word_cards_active': len(changed_cards), 'sentence_cards_unsuspended': 0,
            'new_notes': 0, 'new_cards': 0, 'updated_notes': len(selected)}


def apply(before, selected, content, deck, out):
    if not selected:
        return {'status': 'PASS', 'updated_notes': 0, 'cards_unsuspended': 0, 'mode': 'no-op'}
    # Re-read immediately before writing to detect stale IDs or concurrent study.
    fresh = snapshot(deck)
    if fresh != before:
        raise RuntimeError('Live state changed after preflight; run the dry run again')
    timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = out / f'character_pilot_before_{timestamp}.json'
    write_json(backup, before)
    for item in selected:
        note = before['by_word'][item['word']][0]
        row = content[item['word']]
        fields = {k: row[k] for k in EXAMPLE_FIELDS}
        fields['Source'] = merge_source(field(note, 'Source'), row['Source'])
        call('updateNoteFields', note={'id': item['note_id'], 'fields': fields})
        missing = TAGS - set(note['tags'])
        if missing:
            call('addTags', notes=[item['note_id']], tags=' '.join(sorted(missing)))
    if selected:
        call('unsuspend', cards=[r['card_id'] for r in selected])
    result = verify(before, snapshot(deck), selected, content)
    result['backup'] = str(backup)
    result['selected'] = selected
    write_json(out / f'character_pilot_apply_{timestamp}.json', result)
    if result['status'] != 'PASS':
        raise RuntimeError(json.dumps(result, ensure_ascii=False))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--deck', default='Default')
    parser.add_argument('--frequencies', type=Path, required=True)
    parser.add_argument('--word', action='append', default=[])
    parser.add_argument('--known', action='append', default=[])
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--verify-backup', type=Path, help='Read-only verification against a pre-apply backup')
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    if args.apply and args.verify_backup:
        parser.error('--apply and --verify-backup are mutually exclusive')
    content = {r['Word']: r for r in load_characters()}
    if args.apply and not args.word:
        parser.error('--apply requires explicit --word selections')
    words = args.word or list(content)
    if len(set(words)) != len(words) or set(words) - set(content):
        parser.error('Select unique words from the reviewed ten-character manifest')
    before = snapshot(args.deck)
    if args.verify_backup:
        original = json.loads(args.verify_backup.read_text(encoding='utf-8'))
        selected = [r for r in select(original, words, args.deck, args.known) if r['status'] == 'eligible']
        result = verify(original, before, selected, content)
        result['backup'] = str(args.verify_backup)
        write_json(args.out / 'character_pilot_verification.json', result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if result['status'] != 'PASS':
            raise RuntimeError('Verification failed; inspect local report')
        return
    report = audit(before, args.frequencies, args.deck, args.out)
    report['head'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    report['source_blob'] = subprocess.check_output(['git', 'hash-object', 'word list chinese.txt'], cwd=ROOT, text=True).strip()
    report['targets'] = select(before, words, args.deck, args.known)
    report['mode'] = 'dry-run'
    write_json(args.out / 'suspended_character_audit.json', report)
    selected = [r for r in report['targets'] if r['status'] == 'eligible']
    print(json.dumps({k: report[k] for k in ('head', 'source_blob', 'mode', 'targets', 'suspended_word_recognition', 'suspended_sentence_recognition')}, ensure_ascii=False, indent=2))
    if args.apply:
        print(json.dumps(apply(before, selected, content, args.deck, args.out), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
