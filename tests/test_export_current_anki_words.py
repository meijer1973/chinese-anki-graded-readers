import hashlib
import json

import pytest

from scripts import export_current_anki_words as export


def fake_call(words):
    def call(action, params):
        if action == 'findNotes':
            assert params['query'] == export.QUERY
            return list(range(1, len(words) + 1))
        if action == 'notesInfo':
            return [{'noteId': n, 'modelName': 'Chinese Vocabulary',
                     'fields': {'Word': {'value': words[n - 1]}}} for n in params['notes']]
        if action == 'findCards':
            return list(range(100, 100 + len(words) * 2))
        pytest.fail(f'Unexpected or mutating API: {action}')
    return call


def test_export_unique_words_and_metadata_without_private_ids(tmp_path):
    ranked = tmp_path / 'ranked.txt'
    ranked.write_text('你\n我\n', encoding='utf-8')
    out = tmp_path / 'words.txt'
    metadata = tmp_path / 'metadata.json'
    result = export.export_words(call=fake_call(['我', '你', '你', '他']), word_path=out,
                                 metadata_path=metadata, ranked_source=ranked)
    assert out.read_text(encoding='utf-8').splitlines() == sorted(['我', '你', '他'])
    assert result['note_count'] == 4 and result['unique_word_count'] == 3
    assert result['duplicate_word_note_count'] == 1 and result['duplicate_words'] == ['你']
    assert result['card_count'] == 8
    assert result['live_words_absent_from_ranked_source_count'] == 1
    assert result['ranked_source_words_absent_from_live_deck_count'] == 0
    assert result['words_sha256'] == hashlib.sha256(out.read_bytes()).hexdigest()
    assert json.loads(metadata.read_text(encoding='utf-8')) == result
    assert 'noteId' not in metadata.read_text(encoding='utf-8')


@pytest.mark.parametrize('words', [[], [''], ['字\n词'], ['<b>字</b>']])
def test_invalid_input_does_not_overwrite_export(tmp_path, words):
    out = tmp_path / 'words.txt'
    out.write_text('previous', encoding='utf-8')
    with pytest.raises(ValueError):
        export.export_words(call=fake_call(words), word_path=out, metadata_path=tmp_path / 'meta.json')
    assert out.read_text(encoding='utf-8') == 'previous'


def test_concurrent_word_edit_refuses_export(tmp_path):
    reads = 0
    def call(action, params):
        nonlocal reads
        if action == 'findNotes':
            reads += 1
        return fake_call(['你' if reads == 1 else '我'])(action, params)
    with pytest.raises(RuntimeError, match='changed during export'):
        export.export_words(call=call, word_path=tmp_path / 'words.txt', metadata_path=tmp_path / 'meta.json')
    assert not list(tmp_path.iterdir())
