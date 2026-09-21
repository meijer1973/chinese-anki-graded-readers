import copy

import pytest

from scripts.first_frost import character_pilot as p
from scripts.first_frost import expand_character_pilot as expand
from scripts.first_frost.character_content import load_characters


@pytest.fixture
def environment(monkeypatch):
    content = {r['Word']: r for r in load_characters()}
    payload = expand.note_payload(content['抬'], {'Pinyin': 'tai2', 'Meaning': 'raise', 'Tags': 'manual'}, '123')
    note = {'noteId': 1, 'tags': ['old-provenance'], 'cards': [11, 12],
            'fields': {k: {'value': v} for k, v in payload['fields'].items()}}
    note['fields']['Example']['value'] = 'old'
    cards = [{'cardId': 11 + i, 'note': 1, 'ord': i, 'queue': -1, 'type': 0,
              'due': 100 + i, 'reps': 0, 'lapses': 0, 'interval': 0, 'mod': 10,
              'deckName': 'Default', 'answer': ''} for i in range(2)]
    live = {'templates': {'Word Recognition': {}, 'Sentence Recognition': {}},
            'config': {'new': {'perDay': 2}}, 'notes': [note], 'cards': cards,
            'by_word': {'抬': [note]}}
    source = {w: {**content[w], 'Pinyin': 'mei2', 'Meaning': 'eyebrow', 'Tags': 'manual'}
              for w in ('抬', '眉')}
    monkeypatch.setattr(expand, 'WORDS', ['抬', '眉'])
    monkeypatch.setattr(expand, 'source_rows', lambda: ({'抬': '123', '眉': '4000'}, source))
    monkeypatch.setattr(p, 'snapshot', lambda deck: copy.deepcopy(live))
    return live, content


def test_plan_reuses_review_and_rejects_duplicates(environment, monkeypatch):
    live, content = environment
    live['cards'][0].update(queue=2, type=2, reps=7, due=222)
    monkeypatch.setattr(p, 'call', lambda action, **kw: [True] * len(kw['notes']))
    proposed = expand.plan(live, content)
    assert proposed['summary']['reused_notes'] == 1
    assert proposed['summary']['existing_word_cards_to_unsuspend'] == 0
    assert proposed['summary']['new_notes'] == 1
    assert proposed['additions'][0]['options']['allowDuplicate'] is False
    live['by_word']['抬'].append(copy.deepcopy(live['notes'][0]))
    with pytest.raises(ValueError, match='duplicate-conflict'):
        expand.plan(live, content)


def test_plan_reuses_note_with_siblings_in_separate_subdecks(environment, monkeypatch):
    live, content = environment
    live['cards'][0]['deckName'] = 'Default::Single characters'
    live['cards'][1]['deckName'] = 'Default::Sentences'
    monkeypatch.setattr(p, 'call', lambda action, **kw: [True] * len(kw['notes']))
    proposed = expand.plan(live, content)
    assert proposed['summary']['reused_notes'] == 1
    assert proposed['summary']['new_notes'] == 1


@pytest.mark.parametrize('review', [False, True])
def test_apply_backups_reuses_and_creates_only_scoped_cards(environment, monkeypatch, tmp_path, review):
    live, content = environment
    if review:
        live['cards'][0].update(queue=2, type=2, reps=7, due=222)
    original_review = p.card_state(live['cards'][0])
    mutation_calls = []

    def call(action, **kw):
        if action == 'canAddNotes':
            return [True] * len(kw['notes'])
        if action == 'notesInfo':
            return [n for n in live['notes'] if n['noteId'] in kw['notes']]
        if action == 'cardsInfo':
            return copy.deepcopy([c for c in live['cards'] if c['cardId'] in kw['cards']])
        assert list(tmp_path.glob('expansion_before_*.json'))
        mutation_calls.append(action)
        if action == 'addNotes':
            assert len(kw['notes']) == 1
            payload = kw['notes'][0]
            note = {'noteId': 2, 'tags': payload['tags'], 'cards': [21, 22],
                    'fields': {k: {'value': v} for k, v in payload['fields'].items()}}
            live['notes'].append(note)
            live['by_word']['眉'] = [note]
            for i in range(2):
                live['cards'].append({'cardId': 21 + i, 'note': 2, 'ord': i,
                                      'queue': 0, 'type': 0, 'due': 200, 'mod': 10,
                                      'reps': 0, 'lapses': 0, 'deckName': 'Default',
                                      'answer': '\n'.join(content['眉'][k] for k in p.EXAMPLE_FIELDS)})
            return [2]
        if action == 'updateNoteFields':
            assert kw['note']['id'] == 1
            assert set(kw['note']['fields']) == {*p.EXAMPLE_FIELDS, 'Source'}
            for k, v in kw['note']['fields'].items():
                live['notes'][0]['fields'][k]['value'] = v
            live['cards'][0]['answer'] = '\n'.join(content['抬'][k] for k in p.EXAMPLE_FIELDS)
        elif action == 'addTags':
            live['notes'][0]['tags'].extend(kw['tags'].split())
        elif action in {'suspend', 'unsuspend'}:
            assert kw['cards'] == ([22] if action == 'suspend' else [11])
            for c in live['cards']:
                if c['cardId'] in kw['cards']:
                    c['queue'] = -1 if action == 'suspend' else 0
                    c['mod'] += 1
        else:
            pytest.fail(action)

    monkeypatch.setattr(p, 'call', call)
    before = copy.deepcopy(live)
    proposed = expand.plan(before, content)
    result = expand.apply(before, proposed, content, tmp_path)
    assert result['status'] == 'PASS'
    assert result['new_notes'] == 1 and result['new_cards'] == 2
    assert live['cards'][1]['queue'] == live['cards'][3]['queue'] == -1
    if review:
        assert p.card_state(live['cards'][0]) == original_review
    # A repeat apply must have no live writes and preserve the new-card due values.
    calls_before = len(mutation_calls)
    repeat_before = copy.deepcopy(live)
    repeat = expand.plan(repeat_before, content)
    assert repeat['summary']['notes_to_update'] == repeat['summary']['new_notes'] == 0
    assert expand.apply(repeat_before, repeat, content, tmp_path)['status'] == 'PASS'
    assert len(mutation_calls) == calls_before


def test_preflight_refusal_prevents_apply(environment, monkeypatch):
    live, content = environment
    monkeypatch.setattr(p, 'call', lambda action, **kw: [False])
    with pytest.raises(ValueError, match='duplicate preflight'):
        expand.plan(live, content)


def test_stale_state_prevents_apply(environment, monkeypatch, tmp_path):
    live, content = environment
    monkeypatch.setattr(p, 'call', lambda action, **kw: [True])
    before = copy.deepcopy(live)
    proposed = expand.plan(before, content)
    live['cards'][0]['due'] += 1
    with pytest.raises(RuntimeError, match='Live state changed'):
        expand.apply(before, proposed, content, tmp_path)
    assert not list(tmp_path.iterdir())
