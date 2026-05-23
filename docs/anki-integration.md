# Anki Integration For Stretch Words

Stretch words must flow into Anki safely. The novel workflow does not directly mutate the live Anki collection.

## Existing Deck

The repo already assumes:

- AnkiConnect URL: `http://127.0.0.1:8765`
- Note model: `Chinese Vocabulary`
- Main fields: `Word`, `Pinyin`, `Meaning`, `Example`, `Example Pinyin`, `Example Meaning`, `Source`, `Production Card`, `Sentence Card`, `Frequency Rank`

See `anki/anki_field_schema.md` for the stretch candidate field mapping.

## Export Candidates

Create a review TSV:

```powershell
python scripts/export_stretch_words_for_anki.py --packs data/stretch_packs/general_fiction_100.txt data/stretch_packs/low_fantasy_150.txt data/stretch_packs/shanghai_setting_150.txt data/stretch_packs/professions_social_roles_100.txt data/stretch_packs/urban_objects_100.txt --metadata data/stretch_packs/metadata --existing-anki anki/existing_words.txt --out anki/stretch_word_candidates.tsv --report anki/stretch_word_import_log.json
```

The export:

- excludes core known words
- excludes existing Anki words when `anki/existing_words.txt` is available
- avoids duplicates across packs
- includes metadata when present
- marks each row as `candidate`

Review candidates before import. Use the existing Anki scripts only after review.

Add `--dry-run` to collect counts and missing-metadata warnings without writing the candidate TSV.

## Status Tracking

Use these statuses:

- `candidate`
- `approved`
- `exported`
- `imported`
- `active in Anki`
- `suspended`
- `learned`
- `promoted to core known list`

## Promotion To Core

When words are learned, create a reviewed list and write a new known-word file:

```powershell
python scripts/promote_stretch_words.py --approved anki/learned_stretch_words.txt --core data/known_words.txt --stretch-packs data/stretch_packs --out data/known_words.updated.txt --audit anki/stretch_word_promotion_audit.json
```

Do not rewrite historical manuscript reports. Future books can use the updated known list as core.

Add `--dry-run` to preview promotion without writing the updated known-word file.
