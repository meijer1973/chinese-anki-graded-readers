# Three Chinese subdecks — 24 September 2026

Created `Default::Multi-character words` and moved all 2530 multi-character
Word Recognition cards from Default into it. Default now contains no cards
directly and remains the combined study entry point.

| Subdeck | Cards, including suspended | Retention |
| --- | ---: | ---: |
| Multi-character words | 2530 | 90% |
| Sentences | 4777 | 80% |
| Single characters | 2247 | 95% |

The new child uses the existing Default preset and FSRS parameters, with an
explicit 90% deck retention override matching the cards' previous target.
Existing child settings, daily limits, Deck gathering, card order, note fields,
templates, suspension, learning state, due dates, intervals, memory state,
and review history were preserved. No cards or notes were created or deleted.
The unrelated China Knowledge deck was unchanged.

## Backup and verification

A full collection package was exported with Include media enabled:

`C:\Users\meije\Downloads\Anki-three-subdecks-20260924\collection-before-routing-20260924.colpkg`

- Size: 1548105 bytes.
- SHA-256: `38f72e459d22f82a60c9ebe59f4c000014ca5c01d110ac9dfdad8153928533ab`.
- ZIP integrity and empty media manifest: PASS.
- Isolated restoration into an unsynced test profile: PASS.
- Dry run: exactly 2530 multi-character word moves; no unresolved cases.
- Trial migration and no-op repeat: PASS.
- Live migration: PASS, with the same 2530 moves.
- Preservation comparison: all 9954 collection cards and 16743 review records,
  plus note content, templates, models, media, presets, and global options.
- Effective retention checks: 90%, 80%, and 95% respectively.
- Normal sync and independent final AnkiConnect readback: PASS.
- Final direct Default membership: zero cards.
- Inventory: 4777 unique Chinese notes, 9554 cards, zero duplicate words.

Private restore proofs and per-run snapshots/manifests are retained beside the
backup. Additional readback evidence is in the ignored local-results directory.
The full package is a collection-wide rollback point; restoring it would discard
subsequent work, so preserve later changes before considering a rollback.

## Repository changes and checks

The shared classifier now identifies multi-character targets explicitly as
`multi`. The reusable routing script includes the new 90% destination, so future
imports can be routed into all three children. Imports still begin in Default;
the backup-tested routing step remains required afterward.

Updated the agent guide and Anki workflow documentation to match the live deck.
The tests exercise adding the third child while preserving existing children,
idempotence, unrelated-deck isolation, and rejection of scheduling or memory
changes to moved multi-character cards.

`python -m pytest tests/test_chinese_subdecks.py tests/test_add_chinese_words_to_anki.py -q`
passed: 25 tests and 95 subtests. Two existing pypinyin deprecation warnings
remain. `git diff --check` passed. The live inventory and agent file indexes were
refreshed.
