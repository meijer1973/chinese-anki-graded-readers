# First Frost character-recognition pilot

This workflow implements the first ten recommendations supplied in September 2026:
唇、视、扯、绪、稍、懒、淡、察、渐、弯. The user approved all eligible suspended matches.
The next twenty recommendations and twelve source-gap candidates are audit-only.

## Content and evidence

`anki/first_frost/character_pilot.json` contains the ten original examples, supplied
numbered-tone sentence pinyin, translations, and character-count evidence. It was
transcribed from the supplied `READING_RECOMMENDATIONS.md`; the package's proposed
TSV, audit script, EPUB, and `analysis_metadata.json` were not supplied locally.
The manifest records SHA-256 hashes of the recommendations and frequency table.
It contains no novel quotations, private collection IDs, or study-state exports.
Counts are supplied character occurrences, including compounds and names, not
word frequencies or evidence of mastery. No independent EPUB verification is claimed.

The handoff's July HEAD was `ec4021e44421fea9952f3909c3de3a3ab795fcfe` and its
word-list blob was `acec6f5280a3f039df840cd4b5630ea733cfb5b7`. The local preflight
used HEAD `cfb809f3756b595918f21fb6028bbc493a325076` and working word-list blob
`470536177b42c20bd1541e6f1254efa8636780e6`. Existing uncommitted word-list work
was retained. Selection comes from live card state, not that old rank or an allowlist.

## Dry run and explicit application

```powershell
$env:PYTHONIOENCODING='utf-8'
python scripts/first_frost/character_pilot.py --frequencies C:/Users/meije/Downloads/all_character_frequencies.tsv
```

The audit checks actual model templates, model-wide duplicate notes, deck membership,
queue `-1` suspension, repetitions, and leeches. Buried, already-active, missing,
duplicate, leech, and previously studied targets are reported for separate review.
Use repeated `--known` arguments to exclude user-recognized characters. It also
exports suspended singleton recognition cards with positive EPUB counts, sorted
by count, and audits the reserve/source-gap lists without applying them.

The apply command requires explicit words. For the approved initial batch:

```powershell
python scripts/first_frost/character_pilot.py --frequencies C:/Users/meije/Downloads/all_character_frequencies.tsv --word 唇 --word 视 --word 扯 --word 绪 --word 稍 --word 懒 --word 淡 --word 察 --word 渐 --word 弯 --apply
```

Only eligible Word Recognition IDs are unsuspended. The command updates Example,
Example Pinyin, Example Meaning, and appends truthful original-example provenance
to Source; it adds `reading::first_frost` and `pilot::characters`. Headword fields,
source ranks, existing provenance, and tags are preserved. In particular 稍 retains
shāo/shào and 渐 retains its existing readings. Their contextual examples use shāo
and jiàn respectively. Headword meanings are deliberately not rewritten from a
single contextual example; 淡/懒 acquire the contextual nuance through translation.

No cards or notes are created. Sentence and production card states, all due
positions, review history, FSRS state exposed by AnkiConnect, and daily limits
remain unchanged. Original examples appear on the existing word-card backs.
The command does not run global setup or scheduling routines.

## Persistence and verification

`sentence_example_overrides.py` loads the ten reviewed examples after the earlier
whole-word pilot. The cohorts have no identical headwords; exact sentence-pinyin
overrides prevent automatic pronunciation replacement during TSV rebuilds.
`apply_sentence_example_updates.py` preserves this pilot's original provenance.

The setup script and global scheduler preserve existing suspension by default.
Explicit scoped unsuspension is a separate action; a model-maintenance run must
not undo this word-only choice by activating sibling sentence cards.

Before any mutation, the pilot rechecks live state and writes a timestamped backup
under `anki/first_frost/local_results/`. This directory ignores all private
snapshots, ranked exports, dry runs, and apply reports. Verification compares all
collection card states and all Chinese note fields before and after, permitting
only the selected example/tag changes and selected word-card queue changes.
Anki's normal modification-timestamp advance on unsuspension is also permitted
for those selected cards only; scheduling and review-state fields remain exact.
It also checks the rendered examples on the selected word-card backs. A subsequent
dry run reports the applied targets as already active, without resetting them.

Read-only diagnostics and scoped safety tests:

```powershell
python -m pytest tests/test_character_pilot.py tests/test_first_frost_pilot.py tests/test_anki_card_distribution.py -q
python build_anki_chinese.py
```

## Applied result — 2026-09-12

All ten approved characters were eligible: ten existing notes were reused and
updated, and ten unseen Word Recognition cards were unsuspended. Their ten
Sentence Recognition cards remain suspended. No notes or cards were created;
no duplicates, pronunciation conflicts, or sense conflicts required resolution.
Existing headword readings and definitions were retained as described above.

The final backup-based verification passed across 9,420 collection cards and
4,510 Chinese Vocabulary notes. Due positions, review history, daily limits,
templates, and unrelated cards were unchanged. The initial verification flagged
Anki's normal card modification-timestamp update; the corrected read-only check
passed without further live mutation. Both reports and the original backup are
retained privately. The full test suite passed (168 tests), and a TSV rebuild
retained all ten examples, sentence pinyin strings, and translations exactly.

The post-apply dry run reports all ten targets as already active. The twenty
reserve recommendations and twelve source-gap candidates remain audit-only;
four gaps now exist in the source and eight remain absent. No independent EPUB
verification was possible with the supplied files.
