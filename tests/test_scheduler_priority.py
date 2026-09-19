import copy

import pytest

from scripts import schedule_anki_learning_order as scheduler


@pytest.mark.parametrize('response_style', ['raw', 'wrapped', 'native'])
def test_fallback_uses_one_collision_free_priority_first_queue(monkeypatch, response_style):
    notes = [{'noteId': n, 'fields': {'Word': {'value': word}}, 'tags': tags}
             for n, word, tags in [(1, '普通', []), (2, '目标', ['pilot_first_frost_priority_001']),
                                    (3, '复习', [])]]
    cards = [{'cardId': n * 10 + i, 'note': n, 'ord': i, 'type': 0, 'queue': 0, 'due': 100 + n}
             for n in (1, 2) for i in (0, 1)]
    cards += [{'cardId': 30, 'note': 3, 'ord': 0, 'type': 2, 'queue': 2, 'due': 7},
              {'cardId': 31, 'note': 3, 'ord': 1, 'type': 0, 'queue': -1, 'due': 1}]
    protected = copy.deepcopy(cards[-2:])
    monkeypatch.setattr(scheduler.card_setup, 'load_notes', lambda: copy.deepcopy(notes))
    monkeypatch.setattr(scheduler.card_setup, 'load_cards', lambda: copy.deepcopy(cards))

    def call(action, params):
        if action == 'reposition':
            if response_style == 'native':
                assert params['shiftPosition'] is False
                for due, cid in enumerate(params['cards']):
                    next(c for c in cards if c['cardId'] == cid)['due'] = due
                return None
            raise RuntimeError('unsupported action')
        assert action == 'multi'
        result = []
        for nested in params['actions']:
            data = nested['params']
            assert data['keys'] == ['due']
            next(c for c in cards if c['cardId'] == data['card'])['due'] = data['newValues'][0]
            result.append([True] if response_style == 'raw' else {'result': [True], 'error': None})
        return result

    monkeypatch.setattr(scheduler.card_setup, 'anki', call)
    result = scheduler.apply_learning_order_to_anki(['普通', '目标', '复习'], scheduler.ScheduleConfig())
    active = sorted(cards[:4], key=lambda c: (c['due'], c['cardId']))
    assert [c['cardId'] for c in active] == [20, 21, 10, 11]
    assert len({c['due'] for c in active}) == 4
    assert cards[-2:] == protected
    assert result['queue_order_verified'] is True
    assert result['tagged_priority_cards_repositioned'] == 2


def test_scheduler_rejects_success_response_without_queue_change(monkeypatch):
    notes = [{'noteId': 1, 'fields': {'Word': {'value': '普通'}}, 'tags': []}]
    cards = [{'cardId': 10 + i, 'note': 1, 'ord': i, 'type': 0, 'queue': 0, 'due': 100} for i in (0, 1)]
    monkeypatch.setattr(scheduler.card_setup, 'load_notes', lambda: notes)
    monkeypatch.setattr(scheduler.card_setup, 'load_cards', lambda: cards)
    monkeypatch.setattr(scheduler.card_setup, 'anki', lambda *args: True)
    with pytest.raises(RuntimeError, match='queue'):
        scheduler.apply_learning_order_to_anki(['普通'], scheduler.ScheduleConfig())


@pytest.mark.parametrize('response', [[False], {'result': [False], 'error': None}])
def test_fallback_rejects_false_per_card_response(monkeypatch, response):
    monkeypatch.setattr(scheduler.card_setup, 'anki', lambda *args: [response])
    with pytest.raises(RuntimeError, match='due update failed'):
        scheduler.set_new_card_due_order([10])
