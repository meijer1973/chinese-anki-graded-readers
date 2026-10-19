# Selected vocabulary additions, second batch — 19 October 2026

Checked the user's 200 unique requested entries against the live Chinese
Vocabulary notes, including all Default subdecks. Reused 43 existing notes and
added 157 missing requested entries. Added nine further component-character
notes under the standing character-closure policy: 哨 嗽 嚣 坛 墅 戚 曝 舆 趋.

| Verified result | Count |
| --- | ---: |
| Requested entries | 200 |
| Existing notes reused | 43 |
| Requested new notes | 157 |
| Additional component-character notes | 9 |
| Total notes added | 166 |
| Selected word cards active | 209 |
| Selected sentence cards suspended | 209 |
| Selected active new word cards mixed | 204 |
| All active new cards mixed | 637 |
| Total Chinese Vocabulary notes | 5,272 |
| Single-character word cards | 2,546 |
| Multi-character word cards | 2,726 |
| Sentence cards | 5,272 |

All 43 reused entries already had active word cards and suspended sentence
cards. No existing suspension changes were needed. Five selected word cards
were already in review and retained their schedules.

## Content and source verification

The ranked source now contains 5,074 unique rows. All 4,908 preceding rows and
their generated study fields were preserved. Reviewed the 166 new entries and
curated 113 example/translation pairs, 52 concise meanings, 15 word-reading
overrides and 55 sentence-pinyin corrections. The remaining examples were
reviewed Tatoeba sentences. Added manual dictionary entries for 屏住 and 本次.
Readings include the context-dependent pronunciations of 咽 and corrections
for 屏住、挣脱、曝光、正当 and 下载.

Both TSV exports were rebuilt. Every new study field matched the reviewed
content. No generated export row required meaning review or used a generated
placeholder example. Running `ensure_single_character_notes.py` found zero
missing component characters and added no further notes. Existing live note
content was preserved. Graded-reader allowlists were not expanded.

## Backup, import and routing

Full media-inclusive collection backups passed isolated native Anki restore
verification before import and routing. The media manifest was empty. SQLite
was used only to copy the source database read-only while User 1 was closed.
Live changes used AnkiConnect and native Card APIs.

The guarded importer passed duplicate checks, a dry run and canAddNotes checks
before adding exactly 166 notes. Import verification preserved all 5,106 prior
Chinese notes and all 10,612 prior collection cards. The 166 new sentence cards
were suspended; all new word cards remained active. A separate selected-card
verification confirmed the requested states for all 209 selected notes.

Routing passed a dry run, application in a restored copy and a no-op repeat.
Live routing moved 18 new word cards to `Default::Single characters`, 148 to
`Default::Multi-character words`, and 166 sentence siblings to
`Default::Sentences`. Raw verification checked all 10,944 collection cards and
preserved all 21,842 review entries, stored memory state and scheduling data
apart from the intended deck IDs and native modification metadata. Default
remains an empty combined parent.

## Learning order and final checks

Shuffled within selected single-character, selected multi-character, other
single-character, other multi-character and sentence groups, then spread the
groups proportionally through the active new-card queue. The 204 selected new
word cards are distributed 51, 51, 52 and 50 across the queue's four quarters.
The 637-card pool contains 353 single-character word cards, 277 multi-character
word cards and seven sentence cards that were already active.

Mixing verification compared all 10,944 cards and all 5,272 Chinese notes.
Only active new-card positions and their modification metadata changed.
Review schedules, suspended cards, Ascending position gathering, the combined
10-new-card daily limit and the 95%/90%/80% retention overrides were preserved.
Normal synchronization completed. Fresh live checks confirmed all 418 selected
cards have the correct states and destinations. The refreshed live inventory
contains 5,272 unique headwords and no duplicate headword notes.

Validation included the builder, character closure, Python syntax checks,
guarded import checks, isolated backup restoration, native routing verification,
selected-card preservation checks, new-card order verification, the live
inventory exporter and `git diff --check`.

Private backups, reviewed content, manifests and verification results remain in
ignored `anki/first_frost/local_results/selected_words_batch2_20261019/`.
