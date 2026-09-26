# Missing multi-character word components — 26 September 2026

Created nine Chinese Vocabulary notes for missing characters used in live
multi-character words: **润 傅 妖 巷 摊 浦 砖 蓄 贷**. The 182 characters found
only in example sentences were outside this selection and were not added.

| Character | Existing source word | Source word card | New word card | New sentence card |
| --- | --- | --- | --- | --- |
| 润 | 利润 | Suspended | Suspended | Suspended |
| 傅 | 司机师傅 | Suspended | Suspended | Suspended |
| 妖 | 妖怪 | Suspended | Suspended | Suspended |
| 巷 | 小巷 | Suspended | Suspended | Suspended |
| 摊 | 摊主 | Suspended | Suspended | Suspended |
| 浦 | 黄浦江 | Suspended | Suspended | Suspended |
| 砖 | 地砖 | Suspended | Suspended | Suspended |
| 蓄 | 储蓄 | Suspended | Suspended | Suspended |
| 贷 | 贷款 | Suspended | Suspended | Suspended |

The user requested activation only when an existing active multi-character word
card contains the character. Fresh checks found no qualifying active source
cards, so all 18 new cards remain suspended. Word cards are in
`Default::Single characters`; sentence cards are in `Default::Sentences`.

## Content and validation

- Appended the nine characters at source ranks 4580–4588 and curated concise
  meanings and original examples. Reviewed readings against local CC-CEDICT.
- Rebuilt TSV exports: 4,588 rows, zero missing meanings, zero placeholder examples.
- Ran `ensure_single_character_notes.py`: source character closure complete;
  zero additional notes created and no live learning-order changes.
- The ordinary importer dry run and duplicate preflight passed before adding.
- Final live component audit: **zero** characters in multi-character Word fields
  lacking a standalone card; suspended standalone cards count as present.
- Verified all 4,777 pre-existing Chinese notes and all 9,954 pre-existing cards
  unchanged, including suspension, deck membership, and scheduling.
- Full collection backup, isolated restore, test routing, repeat no-op, and live
  routing verification passed. All 17,019 review records were preserved.
- Final Chinese totals: **4,786 unique notes / 9,572 cards**, comprising 2,256
  single-character word cards, 2,530 multi-character word cards, and 4,786 sentence
  cards. Default has zero direct cards. Duplicate words: zero.
- Normal Anki sync completed. Refreshed both live inventory files.
- Python syntax checks passed for the two edited content-override modules.

Private evidence is ignored under
`anki/first_frost/local_results/component_characters_20260926/`.
The media-inclusive backup and routing evidence remain outside Git under
`C:\Users\meije\Downloads\Anki-components-routing-20260926\`.
Backup: `collection-before-routing-20260926.colpkg`, 1,576,327 bytes,
SHA-256 `fff64ef42b01f9b72083d21fb357a320471ebf2039d4a72eb5eab6482795940a`.
The separate unsynced restore-test profile is
`Subdeck restore test 20260926 components`.
