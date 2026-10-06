# Ghent top-2300 character additions — 6 October 2026

Added the 131 previously missing characters from the original Ghent SUBTLEX-CH
character ranking. Every character in its first 2,300 rows now has a dedicated
Word Recognition card. The original ranking preserves distinct forms such as
妳 and 後; no simplification was applied to the inventory comparison.

| Verified result | Count |
| --- | ---: |
| New notes | 131 |
| New active Word Recognition cards | 131 |
| New suspended Sentence Recognition cards | 131 |
| Top-2300 characters present | 2,300 |
| Top-2300 characters still missing | 0 |
| Total single-character Word Recognition cards | 2,468 |
| Total Chinese vocabulary notes | 4,998 |
| Active new cards mixed | 624 |

The total single-character count exceeds 2,300 because the deck also contains
characters outside this frequency band. Presence in the deck is distinct from
mastery or activation: existing suspension choices were preserved.

## Content and import verification

Appended the approved characters to `word list chinese.txt`, preserving all
4,669 earlier source rows. The source now contains 4,800 unique rows. Added
curated meanings, readings, original example sentences and English translations;
reviewed sentence pronunciations, including polyphonic characters, neutral tones
and 一/不 tone changes. Rebuilt both TSV exports. Existing exported rows were
unchanged, and no row requires meaning review or uses a placeholder example.

The guarded importer passed duplicate and canAddNotes checks, created exactly
131 notes, and suspended only their 131 sentence cards. Before/after checks
preserved all 4,867 existing Chinese notes and all 10,134 existing collection
cards. Character closure passed with no further additions. The refreshed live
inventory contains 4,998 unique headwords with no duplicates.

## Routing, scheduling and preservation

New word cards were routed to `Default::Single characters`; sentence siblings
were routed to `Default::Sentences`. Default remains an empty combined parent.
The 95%/90%/80% retention overrides, Ascending position gathering and combined
10-new-card daily limit were preserved.

Full media-inclusive collection backups passed isolated restore verification.
Because the Computer Use runtime could not initialize, the backups and restore
tests used installed Anki 26.09.2 native APIs through a private CPython 3.13
runtime. Read-only SQLite backups were taken with User 1 closed in the GUI;
the collection had no media files. Routing was tested in the restored copy,
including a no-op repeat, before live application through AnkiConnect's native
Card API wrapper. No live SQL writes were used. Raw before/after comparisons
checked all 10,396 cards and preserved all 18,884 review entries, note content,
stored memory state and scheduling data apart from the intended deck changes.

Randomized within character, multi-character word and sentence groups, then
spread the groups across the active new-card queue. The 131 additions occupy
33, 32, 33 and 33 positions in the four queue quarters. Verification checked
every card and all 4,998 Chinese notes: only the intended active new-card due
positions and modification timestamps changed. Suspended cards and review
schedules were preserved. Normal Anki synchronization completed successfully.

## Reproducibility

- Character source: `SUBTLEX-CH-CHR/SUBTLEX-CH-CHR`, GB18030, original descending
  CHRCount order with source order retained for ties.
- Source SHA-256: `03ffacc65c4d14530338c1bffb72b2e98d06ee23bed14546dc8001ab4bcbb415`.
- Rebuilt with `python build_anki_chinese.py`.
- Closure checked with `python ensure_single_character_notes.py`.
- Syntax checked for the three edited Python content files.
- Refreshed inventory with `python scripts/export_current_anki_words.py`.
- Private backups, import manifests, routing tests, mixing plan and final
  verification are in ignored
  `anki/first_frost/local_results/ghent_131_additions_20261006/`.

The graded-reader vocabulary policy and character-compound allowlist were not
expanded by this Anki addition.
