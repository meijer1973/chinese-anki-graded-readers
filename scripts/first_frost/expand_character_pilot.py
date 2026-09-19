"""Explicitly extend the character pilot; dry-run by default, no global maintenance.

Reuse existing notes (including reviews); create only absent approved characters.
New notes generate both recognition cards, with only their sentence card suspended.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.first_frost import character_pilot as p  # noqa: E402
from scripts.first_frost.character_content import load_characters  # noqa: E402

WORDS = p.RESERVES + p.GAPS
DECK = 'Default'
OUT = p.OUT / 'expansion_20260912'


def source_rows():
    words = (ROOT / 'word list chinese.txt').read_text(encoding='utf-8-sig').splitlines()
    words = [w.strip() for w in words if w.strip()]
    if len(words) != len(set(words)):
        raise ValueError('Duplicate ranked source words')
    with (ROOT / 'anki_chinese_review.tsv').open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle, delimiter='\t'))
    if len(rows) != len({r['Word'] for r in rows}):
        raise ValueError('Duplicate generated TSV words')
    return {w: str(i + 1) for i, w in enumerate(words)}, {r['Word']: r for r in rows}


def note_payload(row, source, rank):
    if any(not source.get(k) for k in ('Pinyin', 'Meaning', 'Tags')):
        raise ValueError(f"Incomplete new headword: {row['Word']}")
    if {'generated', 'needs_meaning_review'} & set(source['Tags'].split()):
        raise ValueError(f"Unreviewed new headword: {row['Word']}")
    fields = {'Word': row['Word'], 'Pinyin': source['Pinyin'], 'Meaning': source['Meaning'],
              **{k: row[k] for k in p.EXAMPLE_FIELDS},
              'Source': p.merge_source(source['Tags'], row['Source']),
              'Frequency Rank': rank, 'Production Card': '', 'Sentence Card': 'yes'}
    return {'deckName': DECK, 'modelName': p.MODEL, 'fields': fields,
            'tags': sorted({'chinese_vocab', 'has_example', *source['Tags'].split(), *p.TAGS}),
            'options': {'allowDuplicate': False}}


def plan(before, content):
    if set(before['templates']) != {'Word Recognition', 'Sentence Recognition'}:
        raise ValueError('Require exactly the two existing recognition templates')
    ranks, source = source_rows()
    targets = p.select(before, WORDS, DECK)
    additions = []
    conflicts = []
    for item in targets:
        word = item['word']
        row = content[word]
        if word not in ranks or word not in source:
            raise ValueError(f'Missing source row; append/rebuild first: {word}')
        if any(source[word][k] != row[k] for k in p.EXAMPLE_FIELDS):
            raise ValueError(f'Curated TSV differs from manifest: {word}')
        if item['status'] == 'missing':
            additions.append(note_payload(row, source[word], ranks[word]))
        elif item['status'] in {'eligible', 'already-active'}:
            note = before['by_word'][word][0]
            # Do not move filtered-deck or sibling cards out of another deck.
            cards = [c for c in before['cards'] if c['note'] == note['noteId']]
            if len(cards) != 2 or any(c['deckName'] != DECK or c.get('odid', 0) for c in cards):
                conflicts.append({'word': word, 'status': 'sibling-card-or-deck-conflict'})
                continue
            fields = {**{k: row[k] for k in p.EXAMPLE_FIELDS},
                      'Source': p.merge_source(p.field(note, 'Source'), row['Source'])}
            item['needs_update'] = (any(p.field(note, k) != v for k, v in fields.items())
                                    or not p.TAGS <= set(note['tags']))
        else:
            conflicts.append(item)
    if conflicts:
        raise ValueError('Unresolved targets: ' + json.dumps(conflicts, ensure_ascii=False))
    if additions and p.call('canAddNotes', notes=additions) != [True] * len(additions):
        raise ValueError('Anki duplicate preflight refused additions')
    return {'targets': targets, 'additions': additions,
            'summary': {'reused_notes': sum(t['status'] != 'missing' for t in targets),
                        'notes_to_update': sum(t.get('needs_update', False) for t in targets),
                        'new_notes': len(additions), 'new_cards': len(additions) * 2,
                        'existing_word_cards_to_unsuspend': sum(t['status'] == 'eligible' for t in targets),
                        'new_sentence_cards_to_suspend': len(additions), 'conflicts': []}}


def verify(before, after, proposed, content, added_ids, created_cards):
    old_notes = {n['noteId'] for n in before['notes']}
    old_cards = {c['cardId'] for c in before['cards']}
    existing_after = {**after, 'notes': [n for n in after['notes'] if n['noteId'] in old_notes],
                      'cards': [c for c in after['cards'] if c['cardId'] in old_cards]}
    existing = [t for t in proposed['targets'] if t['status'] != 'missing']
    unsuspended = {t['card_id'] for t in existing if t['status'] == 'eligible'}
    result = p.verify(before, existing_after, existing, content, unsuspended=unsuspended)
    errors = result['errors']
    if {n['noteId'] for n in after['notes']} != old_notes | set(added_ids):
        errors.append('Unexpected new note membership')
    if {c['cardId'] for c in after['cards']} != old_cards | {c['cardId'] for c in created_cards}:
        errors.append('Unexpected new card membership')
    names = list(after['templates'])
    by_card = {c['cardId']: c for c in after['cards']}
    for payload, nid in zip(proposed['additions'], added_ids, strict=True):
        word = payload['fields']['Word']
        matches = after['by_word'].get(word, [])
        if len(matches) != 1 or matches[0]['noteId'] != nid:
            errors.append(f'New note duplicate or missing: {word}')
            continue
        note = matches[0]
        if {k: p.field(note, k) for k in note['fields']} != payload['fields'] or set(note['tags']) != set(payload['tags']):
            errors.append(f'New note field/tag mismatch: {word}')
        cards = [c for c in created_cards if c['note'] == nid]
        if sorted(c['ord'] for c in cards) != [0, 1] or set(note['cards']) != {c['cardId'] for c in cards}:
            errors.append(f'New note must have exactly two recognition cards: {word}')
        for initial in cards:
            current = by_card.get(initial['cardId'], {})
            expected = p.card_state(initial)
            sentence = names[initial['ord']] == 'Sentence Recognition'
            expected['queue'] = -1 if sentence else 0
            if sentence and 'mod' in expected:
                if current.get('mod', 0) < expected['mod']:
                    errors.append(f'New card timestamp went backwards: {word}')
                expected['mod'] = current.get('mod')
            if (p.card_state(current) != expected or current.get('reps') != 0
                    or current.get('type') != 0 or current.get('deckName') != DECK):
                errors.append(f'Unexpected new card state: {word}')
            if not sentence and any(content[word][k] not in p.unescape(current.get('answer', '')) for k in p.EXAMPLE_FIELDS):
                errors.append(f'New rendered word-card example mismatch: {word}')
    result.update(status='PASS' if not errors else 'ERROR', reused_notes=len(existing),
                  updated_notes=sum(t.get('needs_update', False) for t in existing),
                  new_notes=len(added_ids), new_cards=len(created_cards),
                  existing_word_cards_unsuspended=len(unsuspended), new_word_cards_active=len(added_ids),
                  new_sentence_cards_suspended=len(added_ids),
                  target_word_cards_active=len(existing) + len(added_ids))
    return result


def apply(before, proposed, content, out):
    # Re-plan against the same snapshot to detect edits to reviewed local inputs.
    if plan(before, content) != proposed or content != {r['Word']: r for r in load_characters()}:
        raise RuntimeError('Reviewed local input changed; repeat dry run')
    if p.snapshot(DECK) != before:
        raise RuntimeError('Live state changed; repeat dry run')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = out / f'expansion_before_{stamp}.json'
    p.write_json(backup, {'state': before, 'plan': proposed, 'content': content})
    added_ids = []
    created_cards = []
    if proposed['additions']:
        added_ids = p.call('addNotes', notes=proposed['additions'])
        # Retain outcomes even if Anki partially refuses a batch. Never blind-retry.
        p.write_json(out / f'created_note_ids_{stamp}.json', {'result': added_ids})
        if (not isinstance(added_ids, list) or len(added_ids) != len(proposed['additions'])
                or not all(isinstance(n, int) and n > 0 for n in added_ids)):
            raise RuntimeError('Partial add result; inspect local backup and IDs before retrying')
        new_notes = p.batch_info('notesInfo', 'notes', added_ids)
        created_cards = p.batch_info('cardsInfo', 'cards', [cid for n in new_notes for cid in n['cards']])
        p.write_json(out / f'created_cards_{stamp}.json', created_cards)
        names = list(before['templates'])
        if len(created_cards) != 2 * len(added_ids):
            raise RuntimeError('Unexpected created card count; inspect private report')
        p.call('suspend', cards=[c['cardId'] for c in created_cards if names[c['ord']] == 'Sentence Recognition'])
    for target in proposed['targets']:
        if not target.get('needs_update'):
            continue
        note = before['by_word'][target['word']][0]
        row = content[target['word']]
        fields = {**{k: row[k] for k in p.EXAMPLE_FIELDS},
                  'Source': p.merge_source(p.field(note, 'Source'), row['Source'])}
        if any(p.field(note, k) != v for k, v in fields.items()):
            p.call('updateNoteFields', note={'id': target['note_id'], 'fields': fields})
        missing_tags = p.TAGS - set(note['tags'])
        if missing_tags:
            p.call('addTags', notes=[target['note_id']], tags=' '.join(sorted(missing_tags)))
    eligible_ids = [t['card_id'] for t in proposed['targets'] if t['status'] == 'eligible']
    if eligible_ids:
        p.call('unsuspend', cards=eligible_ids)
    result = verify(before, p.snapshot(DECK), proposed, content, added_ids, created_cards)
    result['backup'] = str(backup)
    p.write_json(out / f'expansion_apply_{stamp}.json', result)
    if result['status'] != 'PASS':
        raise RuntimeError(json.dumps(result, ensure_ascii=False))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--cohort', choices=['next-twenty-and-gaps'])
    parser.add_argument('--out', type=Path, default=OUT)
    args = parser.parse_args()
    if args.apply and not args.cohort:
        parser.error('--apply requires explicit --cohort next-twenty-and-gaps')
    content = {r['Word']: r for r in load_characters()}
    before = p.snapshot(DECK)
    proposed = plan(before, content)
    p.write_json(args.out / 'expansion_dry_run.json', proposed)
    print(json.dumps({'mode': 'dry-run', **proposed['summary']}, ensure_ascii=False, indent=2))
    if args.apply:
        print(json.dumps(apply(before, proposed, content, args.out), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
