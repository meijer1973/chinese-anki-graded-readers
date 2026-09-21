# Chinese subdecks and FSRS

The 21 September 2026 migration keeps the existing `Chinese Vocabulary` note
model and `Default` parent. These are card destinations, not separate note types:

| Cards | Location | Desired retention |
| --- | --- | --- |
| Single-Han-character Word Recognition | `Default::Single characters` | 95% deck override |
| Sentence Recognition | `Default::Sentences` | 80% deck override |
| Multi-character Word Recognition | Existing location, currently `Default` | Existing 90% |

One note's two cards can live in different decks. Study **Default** for the
combined collection; Anki uses each card's home-deck scheduling options.
Nothing is unsuspended by routing. Preserve the user's word-only/sentence-only
choices. No notes/cards, templates, ranks, reader allowlists, or media are added.

## Current configuration

Anki 26.09.2 supports deck-specific retention. Both children use the original
Default preset and fitted FSRS parameters, with only their deck retention
overridden. The original 10-new/500-review daily limits, learning steps 1/10
minutes, relearning step 10 minutes, and sibling-burying preferences remain.
The parent remains limited to **10 new cards total**, not 10 per category when
studying the parent. Child limits are not lower than the parent.

There was **no rescheduling on change**, FSRS optimization, review simulation, or
reset. Existing due dates, intervals, steps, stored memory state, queue positions,
and history remain unchanged. The new retention targets take effect gradually
when cards receive their next real reviews.

New-card gathering remains **Deck** (the pre-migration setting). Consequently,
parent study may gather categories in deck order even though the existing random
due positions are unchanged. To preserve a shuffled cross-category new queue,
an explicitly approved option is **Ascending position** gathering, without
repositioning cards or changing limits. Do not silently change this preference.

## Future notes and duplicate protection

Follow `docs/chinese-vocabulary-anki.md` for reviewed source content, character
closure, duplicate checks, import, and explicitly chosen suspension states.
`deck:Default` searches include descendants. Deck-scoped add-note payloads must
also use `duplicateScopeOptions.checkChildren: true`. The ordinary importer,
character-closure importer, stretch importer, and First Frost importer do this;
the character-pilot expansion uses collection-wide duplicate protection.
First Frost reuse/verification accepts cards anywhere under `Default::`.

Imports still start in Default. No template deck overrides were added: the word
template serves both single- and multi-character vocabulary, so one fixed deck
override would be incorrect. **Future imports are not automatically routed.**
After importing and setting the requested active/suspended cards, run the
reviewed routing procedure below. Do not recreate notes to change their decks.
The current inventory exporter already includes children and remains the full
live-word inventory, not a mastery or frequency list.

## Safe reusable routing procedure

`scripts/reorganize_chinese_subdecks.py` runs inside Anki's documented Debug
Console, using the running collection's supported native API. It is dry-run by
default. `scripts/chinese_card_categories.py` inspects model, actual front
template, and target fields. Presentation markup is removed only for analysis.
Example sentences on the back never change a vocabulary card's category.

Unreviewed models/templates, annotations, alternative spellings, disabled/missing
sentence targets, filtered cards, and materially different source presets are
reported and left in place. Different original presets require a reviewed nested
destination plan; the script does not silently merge them.

1. Pause reviews on every device. Perform a normal sync; stop at any one-way
   conflict and reconcile newer work explicitly. Confirm the intended profile.
2. Export **the entire collection** using File > Export > Anki Collection Package
   (`.colpkg`), with **Include media** enabled. Save a timestamped file outside
   the profile, and record size/SHA-256. Do not use an `.apkg` or media-free
   automatic backup as a substitute.
3. Create a separate `Subdeck restore test <date>` profile with **no sync
   credentials**. Import that full package into the empty test profile, never
   into User 1. Confirm the destructive restore warning only for the empty test.
4. For a modern `.colpkg`, extract/decompress its `collection.anki21b` ZIP entry
   with Zstandard to an external analysis `.anki2`. Python 3.14 provides
   `compression.zstd`. Verify archive integrity, database payload hash, and media
   manifest. Open the analysis DB only with `mode=ro&immutable=1`.
5. In the test profile's Debug Console (Ctrl+Shift+semicolon; execute with
   Ctrl+Enter), use `verify_restore` below. It checks every card, note, review,
   field definition, template, note type, tag, grave, deck, and preset against the
   backup DB. It currently accepts only an empty-media collection; **stop and
   extend explicit media-manifest verification** if media is later introduced.
6. Review the dry-run manifest, representative fields/templates, ambiguous
   cases, suspension/burial counts, and all preset users. Apply in the test copy
   first, verify, then run again into another output directory to prove no-op
   behavior. Never grade cards for this test.
7. Return to the live profile. Dry-run again and apply using a fresh output
   directory. The script rejects a stale backup before a nontrivial change,
   takes a fresh per-run preservation snapshot, and refuses to overwrite an
   earlier application backup. A no-op repeat does not reject ordinary study
   progress against an old installation snapshot.
8. Verify `verification.json`, refresh the deck list with `mw.reset()`, then
   perform a normal sync. Never guess upload/download at a one-way prompt.
   Refresh `scripts/export_current_anki_words.py` if publishing the live inventory.

Illustrative console calls (replace paths and assert the correct profile):

```python
import sys
sys.path.insert(0, "C:/Projects/anki")
from scripts import reorganize_chinese_subdecks as migration

# Only inside the unsynced restored test profile:
migration.verify_restore(
    mw.col, profile_name=mw.pm.name, sync_configured=bool(mw.pm.sync_auth()),
    backup="C:/.../collection-TIMESTAMP.colpkg",
    backup_database="C:/.../backup-analysis.anki2",
    out="C:/.../restore-verification.json",
)

# Test copy first, then the explicitly checked live profile:
migration.migrate(
    mw.col, profile_name=mw.pm.name,
    backup_verification="C:/.../restore-verification.json",
    out_dir="C:/.../unique-run-directory", apply=False,
)
# After reviewing the dry run, repeat with apply=True.
```

Keep all detailed manifests/snapshots outside Git: they contain private card IDs,
content, review history and scheduling data. Do not rerun the full First Frost
content installer or global scheduler merely to move cards.

### Native move implementation

Anki 26.09.2's native `set_deck()` path may recompute FSRS memory state.
AnkiConnect's installed `changeDeck` implementation directly writes SQL, which
this migration disallows. Instead, the script loads native Card objects, changes
**only** `card.did`, and submits them through `col.update_cards()`. Native deck
updates set integer-percent retention overrides without rescheduling.
The isolated full-collection test verifies that the complete stored card state,
including the raw FSRS `data` field, remains byte-for-byte unchanged except the
deck ID and native sync metadata. Non-card tables are compared exactly.

## Exact rollback for the 21 September migration

Backup:
`C:\Users\meije\Downloads\Anki-subdeck-migration-20260921\collection-before-migration-20260921-104354.colpkg`

Size: **1,526,714 bytes**. SHA-256:
`c2caf2b75a5a90bb56a8dd124ccb9ae9a42089d4625c06df334f9731aeacc964`.

Manifest and baseline are in the same folder under `live/`; the separate restore
proof is `restore-verification.json`. Keep these and the backup after success.

1. Stop reviewing and syncing on **all** devices. Export the current collection
   including media to another timestamped package to preserve any later work.
2. In desktop Anki, use File > Switch Profile and open **User 1**. Check that
   this really is the profile to roll back. Use File > Import and choose the
   exact backup above. Approve replacement only after preserving later work.
3. This restores the **entire collection**, including China Knowledge, and
   **discards all changes/reviews since the backup**. It is not a selective
   deck-only undo. Verify restored counts, history, options and representative
   cards before reconnecting other devices.
4. Inventory/export any newer work on other devices first. Do not let their
   post-backup state silently re-enter the restored collection. Choose the
   authoritative collection explicitly. If the reviewed rollback is to replace
   AnkiWeb, deliberately upload that desktop collection, then deliberately
   download it to the other devices; those choices discard divergent work and
   require approval. Do not make these decisions automatically.
5. Resume normal sync/review only when all devices agree. The retained test
   profile is unsynced; never connect it to AnkiWeb.

References: [manual full backups](https://docs.ankiweb.net/backups.html#manual-colpkg-backups),
[deck options, retention and subdecks](https://docs.ankiweb.net/deck-options.html),
[Debug Console](https://docs.ankiweb.net/misc.html#debug-console),
[26.09.2 native card operations](https://github.com/ankitects/anki/blob/26.09.2/rslib/src/card/mod.rs).
