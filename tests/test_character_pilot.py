import copy
import json

import pytest

import setup_production_sentence_cards as setup
from scripts.first_frost import character_pilot as pilot
from scripts.first_frost.character_content import load_characters


def state():
    row = load_characters()[0]
    note = {'noteId': 1, 'tags': ['existing-provenance'], 'cards': [11, 12, 13],
            'fields': {k: {'value': v} for k, v in {
                'Word': row['Word'], 'Pinyin': 'chun2', 'Meaning': 'lip',
                'Example': '旧句子', 'Example Pinyin': 'old', 'Example Meaning': 'old',
                'Source': 'original-source', 'Frequency Rank': '3600',
                'Production Card': '', 'Sentence Card': 'yes'}.items()}}
    cards = [{'cardId': 11 + i, 'note': 1, 'ord': i, 'queue': -1, 'type': 0,
              'due': 100 + i, 'reps': 0, 'lapses': 0, 'interval': 0, 'factor': 2500,
              'deckName': 'Default', 'answer': '', 'mod': 10} for i in range(3)]
    # Production is deliberately before Word Recognition: never assume ordinal 0.
    return {'templates': {'Meaning Recall': {}, 'Word Recognition': {}, 'Sentence Recognition': {}},
            'config': {'new': {'perDay': 2}}, 'notes': [note], 'cards': cards,
            'by_word': {row['Word']: [note]}}


def test_selection_uses_named_template_and_excludes_buried_leech_and_duplicates():
    data = state()
    assert pilot.select(data, ['唇'], 'Default')[0]['card_id'] == 12
    data['cards'][1]['queue'] = -2
    assert pilot.select(data, ['唇'], 'Default')[0]['status'] == 'buried'
    data['cards'][1]['queue'] = -1
    data['notes'][0]['tags'].append('leech')
    assert pilot.select(data, ['唇'], 'Default')[0]['status'] == 'leech-needs-review'
    data['by_word']['唇'].append(copy.deepcopy(data['notes'][0]))
    assert pilot.select(data, ['唇'], 'Default')[0]['status'] == 'duplicate-conflict'
    assert pilot.select(data, ['唇'], 'Default', known=['唇'])[0]['status'] == 'user-known'


def test_scoped_apply_backs_up_before_mutation_and_preserves_other_cards(monkeypatch, tmp_path):
    live = state()
    before = copy.deepcopy(live)
    selected = pilot.select(before, ['唇'], 'Default')
    content = {r['Word']: r for r in load_characters()}
    calls = []

    def mutate(action, **params):
        assert list(tmp_path.glob('character_pilot_before_*.json'))
        calls.append(action)
        if action == 'updateNoteFields':
            assert set(params['note']['fields']) == {*pilot.EXAMPLE_FIELDS, 'Source'}
            for k, v in params['note']['fields'].items():
                live['notes'][0]['fields'][k]['value'] = v
            live['cards'][1]['answer'] = '\n'.join(content['唇'][k] for k in pilot.EXAMPLE_FIELDS)
        elif action == 'addTags':
            live['notes'][0]['tags'].extend(params['tags'].split())
        elif action == 'unsuspend':
            assert params['cards'] == [12]
            live['cards'][1]['queue'] = 0
            live['cards'][1]['mod'] += 1
        else:
            pytest.fail(f'Unapproved mutation {action}')

    monkeypatch.setattr(pilot, 'snapshot', lambda deck: copy.deepcopy(live))
    monkeypatch.setattr(pilot, 'call', mutate)
    result = pilot.apply(before, selected, content, 'Default', tmp_path)
    assert result['status'] == 'PASS'
    assert live['cards'][0]['queue'] == live['cards'][2]['queue'] == -1
    assert live['notes'][0]['fields']['Frequency Rank']['value'] == '3600'
    assert calls == ['updateNoteFields', 'addTags', 'unsuspend']
    assert pilot.select(live, ['唇'], 'Default')[0]['status'] == 'already-active'
    # The verifier must catch a review-date change, even if unsuspension succeeded.
    live['cards'][2]['due'] += 1
    assert pilot.verify(before, live, selected, content)['status'] == 'ERROR'


def test_stale_snapshot_refuses_all_mutation(monkeypatch, tmp_path):
    before = state()
    live = copy.deepcopy(before)
    live['cards'][1]['queue'] = 0
    monkeypatch.setattr(pilot, 'snapshot', lambda deck: live)
    monkeypatch.setattr(pilot, 'call', lambda *a, **k: pytest.fail('Must not mutate stale state'))
    with pytest.raises(RuntimeError, match='changed after preflight'):
        pilot.apply(before, pilot.select(before, ['唇'], 'Default'), {}, 'Default', tmp_path)
    assert not list(tmp_path.iterdir())


def test_model_setup_preserves_suspension_by_default(monkeypatch):
    monkeypatch.setattr(setup, 'anki', lambda *a, **k: pytest.fail('Must preserve suspension'))
    setup.unsuspend_cards([12, 13])


def test_global_scheduler_preserves_suspended_cards(monkeypatch):
    from scripts import schedule_anki_learning_order as scheduler
    data = state()
    monkeypatch.setattr(setup, 'load_notes', lambda: data['notes'])
    monkeypatch.setattr(setup, 'load_cards', lambda: data['cards'])
    monkeypatch.setattr(setup, 'anki', lambda *a, **k: pytest.fail('No mutations for fully suspended queue'))
    monkeypatch.setattr(setup, 'unsuspend_cards', lambda *a, **k: pytest.fail('No unsuspend attempt'))
    result = scheduler.apply_learning_order_to_anki(['唇'], scheduler.ScheduleConfig())
    assert result['cn_to_en_cards_unsuspended'] == 0


def test_rebuild_keeps_selected_original_examples_and_polyphonic_headword():
    from sentence_example_overrides import SENTENCE_EXAMPLE_OVERRIDES, SENTENCE_PINYIN_OVERRIDES
    from apply_sentence_example_updates import source_fields_for_note
    for row in load_characters():
        assert SENTENCE_EXAMPLE_OVERRIDES[row['Word']] == (row['Example'], row['Example Meaning'])
        assert SENTENCE_PINYIN_OVERRIDES[row['Example']] == row['Example Pinyin']
    note = state()['notes'][0]
    row = load_characters()[0]
    result = source_fields_for_note(note, {**row, 'Source': 'generic rebuild'})
    assert result['Source'] == 'original-source | ' + row['Source']
