# Chinese subdeck migration — PASS

Completed on 21 September 2026 in Anki 26.09.2, profile **User 1**.
The repository and attached plan agree: retain Default, the Chinese Vocabulary
model, existing notes/cards/content, and the frequency-ranked source.

| Location | Cards | Moved | Active | Suspended | Retention |
| --- | ---: | ---: | ---: | ---: | ---: |
| Default: multi-character vocabulary | 2,400 | 0 | 738 | 1,662 | unchanged 90% |
| Default::Single characters | 2,203 | 2,203 | 831 | 1,372 | 95% |
| Default::Sentences | 4,603 | 4,603 | 1,318 | 3,285 | 80% |
| Chinese total | 9,206 | 6,806 | 2,887 | 6,319 | per home deck |

No buried or filtered cards; no ambiguous classifications or preset conflicts.
No notes/cards added, deleted, cloned, reset, answered, suspended or unsuspended.
The Chinese cohort remains **4,603 notes**, and the full collection remains
**5,003 notes / 9,606 cards / 16,199 review-log entries**. China Knowledge is
unchanged. Refreshed inventory: 4,603 unique words, zero duplicate-word notes;
word-list SHA-256 `c4dcca891a422c4ecf561738faacd0b58e095547ca41f2c795a473e9a78be10f`.

## Verification

- Full media-inclusive collection export restored into the isolated unsynced
  `Subdeck restore test 20260921` profile. All ten checked database tables matched
  the decompressed backup, including all review history, decks and presets.
- Media was included; this collection has zero media files and an empty manifest.
- Native trial migration passed; a second application made zero moves or changes.
- Immediately before live application, all relevant live records/settings matched
  the restore-verified backup. A separate fresh live baseline was then saved.
- Live verification passed: all IDs, fields, tags, templates, flags, suspension,
  due positions/dates, intervals, learning states and raw FSRS memory data retained.
  Only intended card deck IDs and native modification/sync metadata changed.
- Original fitted FSRS parameters and presets retained. Deck-specific 95%/80%
  targets were checked through Anki's native effective deck-options API.
- Parent new-card allowance remains 10, review allowance 500. Learning/relearning
  and sibling-burying settings are unchanged. Default remains combined study.
- No rescheduling on change: new targets take effect on subsequent normal reviews.
- New-card gather order remains Deck; existing randomized positions are preserved,
  but category gathering may now follow deck order. Cross-category Ascending
  position gathering was not silently enabled.
- Normal AnkiWeb sync completed with no error or one-way prompt. Sync other
  devices before resuming their reviews. The test profile remains unsynced.
- A separate post-sync audit passed: all records still match the verified result
  (apart from card sync sequence numbers); the effective targets and limits match.
- Repository tests (206 passed) and subdeck-aware duplicate/reuse checks passed. Private
  card-level data and backup files were not added to Git.

## Backup and artifacts

Full backup (outside the working profile):
`C:\Users\meije\Downloads\Anki-subdeck-migration-20260921\collection-before-migration-20260921-104354.colpkg`

Size **1,526,714 bytes**; SHA-256
`c2caf2b75a5a90bb56a8dd124ccb9ae9a42089d4625c06df334f9731aeacc964`.

The same directory retains `restore-verification.json`, `backup-analysis.anki2`,
`trial/`, `trial-repeat/`, and `live/`. The live folder contains the dry-run
manifest, fresh before/after snapshots, original settings and review records,
card-ID/note-ID destination manifest, and `verification.json`.
It also contains `post_sync_snapshot.json` and `post_sync_verification.json`.

Future imports still enter Default and must be routed afterward; this is not an
automatic hook. See [the reusable procedure and exact rollback instructions](../docs/chinese-subdecks-fsrs.md).
Rollback requires stopping reviews/sync, preserving later work, and importing the
exact full backup into User 1. **All changes since the backup are discarded**,
including changes outside Chinese. Reconcile other devices explicitly before
normal reviewing resumes; never guess one-way upload/download direction.
