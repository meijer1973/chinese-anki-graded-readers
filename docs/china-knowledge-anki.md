# China Common Knowledge Anki Deck

This workflow builds a bilingual general-knowledge deck about China. It tests knowledge, not isolated word translation. Every source note contains a Chinese and English question, a short bilingual answer, a fuller bilingual explanation, taxonomy, source metadata, and a stable `Knowledge ID`.

The deck is completely separate from the Chinese vocabulary, Hindi, and Spanish resources.

## Fixed Live Identifiers

- Deck: `China Knowledge`
- Note type: `China Knowledge Bilingual`
- Options preset: `China Knowledge - 5 new cards`
- Template: `Knowledge Recognition`
- Managed tag root: `china_knowledge`

The installer does not offer overrides for these names. This keeps the mutation boundary auditable. It accepts only an AnkiConnect URL and alternate source paths.

To rename a not-yet-installed deck, change `DECK_NAME` in `scripts/china_knowledge/config.py` and update the corresponding documentation and tests before validation. Renaming an existing live install is a separate migration: do not change the constant and let the old deck become unmanaged. First export or back up it, decide whether its stable-ID notes should move or remain, add an explicit guarded migration, and verify all protected resources. `MODEL_NAME` and `OPTIONS_PRESET_NAME` should normally change with the deck name so the namespace remains isolated.

## Source Package

- Canonical hand-edited data: `anki/china_knowledge/china_knowledge_400.tsv`
- Source catalog: `anki/china_knowledge/china_knowledge.sources.json`
- Deterministic generated payload: `anki/china_knowledge/generated/china_knowledge_import.json`
- Representative test fixture: `tests/fixtures/china_knowledge_sample.tsv`

The 400-note editorial baseline has this fixed distribution:

| Category | Notes |
| --- | ---: |
| Geography | 65 |
| History | 90 |
| Government | 35 |
| Economy | 55 |
| Society | 40 |
| Culture | 45 |
| Language | 25 |
| Science, technology, and environment | 45 |

Facts are independently phrased bilingual summaries. The catalog records exact URLs, organizations, source type, and check dates. Durable claims are preferred; the small number of volatile claims use an `as_of::*` tag and a date. Sources include primary or institutional material from bodies such as the National People's Congress, National Bureau of Statistics, UNESCO, World Bank, WTO, IEA, CNSA, and BeiDou.

## Field Schema

The live note type has these fields in this exact order:

1. `Knowledge ID`
2. `Chinese Question`
3. `English Question`
4. `Chinese Answer`
5. `English Answer`
6. `Chinese Explanation`
7. `English Explanation`
8. `Category`
9. `Subcategory`
10. `Era`
11. `Region`
12. `Difficulty`
13. `Source`
14. `Source Date`
15. `Fact Checked`
16. `Tags`

`Knowledge ID` is the update key. Do not change an existing ID merely to improve wording; an update with the same ID preserves its Anki note ID, card, and review history. `Era` and `Region` may be blank when they do not apply. The other content and provenance fields are required.

The initial schema intentionally has no audio or image field. Future media support should be additive: add explicit `Audio` or `Image` fields in a reviewed schema migration, keep existing IDs stable, update the template and media validator together, and test old notes with blank media fields. Do not hide filenames or TTS directives in current text fields.

## Recognition Card

The front shows the Chinese question first and more prominently, followed by the English question in smaller type. The back repeats the front, shows both short answers, then both explanations. Category, era, region, and collapsed source metadata appear below.

There is exactly one recognition template, so each source note creates exactly one card. No reverse, production, media, audio, or TTS card exists. Styling uses system fonts, responsive sizes, mobile spacing, and explicit light/dark colors.

## Validation and Generated Import

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts/china_knowledge/validate_china_knowledge.py
python scripts/china_knowledge/validate_china_knowledge.py --write-import anki/china_knowledge/generated/china_knowledge_import.json
```

The validator checks exact row and category counts, the exact 16-column UTF-8 TSV schema, stable unique IDs, required bilingual fields, valid taxonomy and ISO dates, source-catalog references, plain text and NFC normalization, answer length, duplicate and near-duplicate prompts, and detectable bilingual number conflicts. Media, HTML, and TTS references are rejected.

The generated JSON is sorted by `Knowledge ID` and can be recreated byte-for-byte from the TSV. Edit the TSV and source catalog, not the generated file.

## Safe Preview, Apply, and Verification

An offline preview validates the source without contacting Anki:

```powershell
python scripts/china_knowledge/setup_china_knowledge_anki.py --offline-preview
```

The default command is a read-only live dry run:

```powershell
python scripts/china_knowledge/setup_china_knowledge_anki.py
python scripts/china_knowledge/setup_china_knowledge_anki.py --dry-run
```

It inventories the target and protected resources and reports how many notes would be created, updated, skipped, or rejected. If Anki or AnkiConnect is unavailable, it writes a blocked report without falling back to mutation.

Apply is deliberately explicit:

```powershell
python scripts/china_knowledge/setup_china_knowledge_anki.py --apply
```

Then inspect without mutation:

```powershell
python scripts/china_knowledge/setup_china_knowledge_anki.py --verify-only
```

The AnkiConnect endpoint defaults to `http://127.0.0.1:8765`; use `--anki-connect-url` for another endpoint.

## Isolation and Update Safety

Before apply, the installer snapshots `Default` with `Chinese Vocabulary`, `Hindi` with `Hindi Vocabulary`, and `Spanish` with `Spanish Vocabulary`. Snapshots include note and card IDs, field values, tags, templates, styling, review scheduling fields, and deck-options configuration. Apply passes only when all three structured after-snapshots are identical.

The runtime mutation guard allows only the fixed China Knowledge deck, note type, preset, and registered target note/config IDs. It rejects protected or unregistered IDs and any non-whitelisted mutation action. An incompatible existing target deck, extra target subdeck, wrong field schema, extra template, unrelated note, duplicate live ID, or target-model note outside the target deck causes a safe failure before mutation.

Existing source IDs are updated in place. Missing notes are added. Notes present live but absent from the current source are reported and never silently deleted. Unrelated tags are preserved. Before field updates, managed live notes are backed up to `anki/china_knowledge/reports/china_knowledge_managed_notes_before_update.tsv`.

## Five New Cards Per Day

The installer clones the new deck's inherited options preset, renames the clone `China Knowledge - 5 new cards`, assigns it only to this deck, and changes only `new.perDay` to `5`. It never edits a protected or shared preset. With one template, five new cards also means five new knowledge notes per day.

To change the daily limit intentionally, update `NEW_CARDS_PER_DAY` and `OPTIONS_PRESET_NAME` in `scripts/china_knowledge/config.py`, adjust the documentation and tests, validate, dry-run, apply, and verify. Changing the number in Anki alone will be restored by the next apply.

## Adding or Revising Facts

1. Add or edit a row in the canonical TSV, retaining an existing `Knowledge ID` for factual or wording corrections.
2. Use a new stable lowercase hyphenated ID for a genuinely new fact.
3. Add every new source to the JSON catalog and cite its source ID in the row.
4. Keep Chinese and English meaning aligned; include matching digits in both sides when a fact depends on a number or date.
5. Mark volatile statements with an `as_of::YYYY` tag and update `Source Date` and `Fact Checked` when re-reviewed.
6. Update the expected count and category target intentionally if the deck expands beyond 400.
7. Regenerate the import payload, run focused and full tests, preview, and review the proposed count before apply.

## Recovery

If validation fails, no live mutation begins. Correct the source row or catalog entry and rerun validation.

If apply stops before adding notes, inspect the apply report and resolve the incompatible deck, note type, or preset manually; the script does not delete or convert it. If a network or Anki failure interrupts a partial apply, keep Anki closed to other edits, preserve the managed-note backup, restart AnkiConnect, rerun the default dry run, then rerun `--apply`. Stable IDs make the retry idempotent: compatible existing notes update or skip, while only missing IDs are added.

Never recover by deleting the protected vocabulary decks or by importing the generated JSON through an unrelated note type.

## Tests

Run the focused suite:

```powershell
python -m unittest tests.test_china_knowledge_data tests.test_china_knowledge_templates tests.test_china_knowledge_setup tests.test_china_knowledge_safety -v
```

The suite covers the full dataset and small fixture, deterministic rendering, one-card templates, no media/TTS, dry-run immutability, exact note/card counts, stable-ID updates, second-run idempotency, dedicated options, incompatible-target failure, the mutation guard, and unchanged Chinese, Hindi, and Spanish resources.
