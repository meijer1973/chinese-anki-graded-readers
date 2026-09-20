# Chinese Vocabulary Anki Workflow

This is the reviewed procedure for adding ordinary ranked Chinese vocabulary notes to the live Anki collection. It manages the `Default` deck and the `Chinese Vocabulary` note type.

The note type generates only two card types:

- `Word Recognition`
- `Sentence Recognition`, when both `Example` and `Example Meaning` are populated

There is no `Meaning Recall` card template. `setup_production_sentence_cards.py` removes that legacy template if it is present. Removing a template also removes its existing cards; the setup script writes `production_sentence_setup_backup.tsv` before changing the model.

## Latest Live Deck Inventory

`anki/current_deck_words.txt` is the complete unique Word-field inventory from the
latest live Default / Chinese Vocabulary export, including suspended and buried
cards. `anki/current_deck_words.metadata.json` records the UTC export timestamp,
note/card/unique-word counts, duplicate findings, ranked-source comparison, and
SHA-256 hashes. The plain-text list is sorted by Unicode, not learning order or
frequency, and contains no card IDs, study schedules, or review history.

```powershell
python scripts/export_current_anki_words.py
```

This is read-only against Anki and requires AnkiConnect. Two consistent membership
reads are required before replacing the latest export; blank/malformed Word fields
or changed membership stop the export. Duplicate notes are reported in metadata
while the plain list contains each word only once. Refresh after vocabulary
additions/removals and publish both files together. Deck membership does not mean
the learner knows the word. Never use this inventory to silently expand reader
allowlists or replace the ranked source.

The 20 September 2026 export has 4,603 unique words / notes and 9,206 cards. Its
198 words absent from the 4,405-entry ranked source demonstrate why the source
list alone is not a full live-deck inventory; all ranked-source words are present.

## 1. Add The Ranked Source Word

Add the word once, at its intended frequency-rank position, in `word list chinese.txt`. The line number is the live `Frequency Rank`.

Duplicate source words are errors. `build_anki_chinese.py` and the live importer both stop and report the duplicate instead of silently discarding it.

## 2. Curate Fields

The builder gets normal pinyin and meanings from CC-CEDICT and looks for a suitable Tatoeba sentence. Curate exceptions in:

- `MANUAL_ENTRIES` in `build_anki_chinese.py` for pinyin/meaning entries missing from the dictionary;
- `MEANING_OVERRIDES` in `apply_meaning_cleanup_updates.py` for concise meanings;
- `SENTENCE_EXAMPLE_OVERRIDES` in `sentence_example_overrides.py` for the Chinese sentence and English translation;
- `SENTENCE_PINYIN_OVERRIDES` in `sentence_example_overrides.py` for exceptional sentence readings.

## 3. Build And Review

```powershell
$env:PYTHONIOENCODING='utf-8'
python build_anki_chinese.py
```

Review the target row in `anki_chinese_review.tsv` and the counts in `enrichment_report.txt`. Do not import a row tagged `needs_meaning_review` or `generated`. The guarded importer rejects both.

## 4. Normalize The Card Model

With Anki and AnkiConnect running:

```powershell
python setup_production_sentence_cards.py
```

This creates or updates the sentence template, enables sentence-card generation for complete notes, removes the legacy `Meaning Recall` template, and preserves existing recognition-card suspension and burial. Activating a word card does not authorize activating its sentence sibling.

## 5. Duplicate Preflight

Dry-run the exact word before adding it:

```powershell
python scripts/add_chinese_words_to_anki.py --word 新词
```

The preflight checks:

- the ranked source contains the word exactly once;
- the generated review TSV contains the word exactly once;
- required fields are populated and reviewed;
- the live deck contains zero or one note for the word;
- the note type has only the two managed recognition templates.

If the word already exists once, it is reported under `already_in_deck` and is not added. Two or more matching live notes are a hard error. Before mutation, the importer also calls Anki's `canAddNotes`; the final `addNotes` request uses `allowDuplicate: false` with deck-scoped duplicate checking.

## 6. Add The Note

Only after the dry run reports the intended word under `would_add`:

```powershell
python scripts/add_chinese_words_to_anki.py --word 新词 --apply
```

Repeat `--word` to add several reviewed words in one checked operation. The importer fills all live fields, enables the sentence card, assigns the source-list rank, adds managed tags, and verifies that exactly one live note exists afterward.

## 7. Enforce Character Coverage And Study Order

After adding a multi-character word:

```powershell
python ensure_single_character_notes.py
python scripts/audit_anki_card_distribution.py
python scripts/schedule_anki_learning_order.py
```

The first command enforces the repository policy that each Hanzi used by a multi-character word also has a standalone note. The scheduler changes new-card order without changing source frequency ranks.
