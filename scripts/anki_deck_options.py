"""Read-only preset ownership checks shared by isolated deck installers."""
from __future__ import annotations

import re
from uuid import uuid4


def managed_preset(name, base):
    return isinstance(name, str) and (name == base or re.fullmatch(re.escape(base) + r' \(private [0-9a-f]{32}\)', name) is not None)


def clone_preset_name(base, other_configs):
    # Some backends return the existing ID for an already-used preset name.
    # Do not rename the preset still used by another deck.
    return f'{base} (private {uuid4().hex})' if any(c.get('name') == base for c in other_configs.values()) else base


def other_deck_configs(read, target_deck, error_type=RuntimeError):
    decks = read('deckNamesAndIds')
    if not isinstance(decks, dict):
        raise error_type('Cannot enumerate all deck preset users safely')
    result = {}
    for name in sorted(decks):
        if name == target_deck:
            continue
        config = read('getDeckConfig', {'deck': name})
        if not isinstance(config, dict) or config.get('id') is None:
            raise error_type(f'Cannot inspect options preset for other deck {name!r}')
        result[name] = config
    return result


def assert_other_configs_unchanged(read, target_deck, before, private_id, error_type=RuntimeError):
    current = other_deck_configs(read, target_deck, error_type)
    if any(int(config['id']) == private_id for config in current.values()):
        raise error_type(f'{target_deck} options preset is still shared with another deck')
    if current != before:
        raise error_type(f'Other deck options changed while configuring {target_deck}')
