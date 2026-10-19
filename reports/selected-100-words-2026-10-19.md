# Selected vocabulary additions — 19 October 2026

Checked the user's 100 unique requested entries against the live Chinese
Vocabulary note type, including every Default subdeck. Reused 52 existing notes
and added exactly 48 missing notes, all for multi-character words or phrases.
No additional component-character notes were needed.

| Verified result | Count |
| --- | ---: |
| Requested entries | 100 |
| Existing notes reused | 52 |
| New notes | 48 |
| Existing word cards unsuspended | 26 |
| Existing sentence cards newly suspended | 8 |
| Selected word cards active after completion | 100 |
| Selected sentence cards suspended after completion | 100 |
| Selected active new word cards included in mixing | 79 |
| All active new cards mixed | 471 |
| Total Chinese Vocabulary notes | 5,106 |
| Duplicate headwords in refreshed inventory | 0 |

The 79 selected new word cards comprise the 48 additions, 26 newly unsuspended
cards and five already-active new cards. The other 21 selected word cards are
review cards and retained their schedules.

## Content and source

The ranked source now contains 4,908 unique rows. All 4,860 preceding rows and
their generated study fields were preserved. Added concise meanings, common
readings, original example sentences, English translations and reviewed sentence
pinyin for the 48 additions. CC-CEDICT was consulted during curation. The new
entries include explicit readings for 结实、嘟囔、拉扯、媳妇 and 胡萝卜.

The builder regenerated both TSV exports. Every new study field matched its
curated source. No export row used a placeholder example or required meaning
review. Character closure found no missing characters and created no extra notes.
Existing live note content was preserved.

## State changes and routing

Full media-inclusive collection backups passed isolated native Anki restore
verification before import and routing. The media manifest was empty. SQLite
was used only to create read-only source backups while User 1 was closed in the
GUI. Live changes used AnkiConnect and native Anki Card APIs.

The guarded importer passed a dry run and canAddNotes checks before adding the
48 notes. Import verification preserved all 5,058 preceding Chinese notes and
all 10,516 preceding collection cards. A separate selected-card pass unsuspended
26 existing word cards and suspended eight existing sentence cards. All other
card states and all note content were preserved during that pass.

New word cards were routed to `Default::Multi-character words`; their sentence
siblings were routed to `Default::Sentences`. Routing passed a dry run, an
isolated-copy application and a no-op repeat before live application. Raw
verification checked all 10,612 collection cards and preserved all 21,842 review
entries, stored memory state and scheduling data apart from intended deck IDs.
Default remains an empty combined parent.

## Learning order and final verification

Shuffled within selected single-character, selected multi-character, other
single-character, other multi-character and sentence groups, then spread those
groups proportionally through the active new-card queue. The 79 selected new
word cards occur 19, 21, 20 and 19 times across the four queue quarters.

Before/after comparisons checked all 10,612 cards and all 5,106 Chinese notes.
Only active new-card due positions and their modification metadata changed
during mixing. Review schedules and suspended cards were preserved. Ascending
position gathering, the combined 10-new-card daily limit and 95%/90%/80% deck
retention overrides were preserved. Normal synchronization completed, followed
by fresh live checks confirming all 100 requested word/sentence card pairs have
the requested states and correct destinations.

Validation included the builder, `ensure_single_character_notes.py`, Python
syntax checks for edited content files, guarded import checks, backup restoration,
native routing verification, selected-card preservation checks, new-card order
verification, `export_current_anki_words.py` and `git diff --check`.

Private manifests, backups and verification details remain in ignored
`anki/first_frost/local_results/selected_words_20261019/`. Graded-reader vocabulary
allowlists and policy were not expanded.

## New notes

丝毫 结实 宠物 鞠躬 游走 草丛 边缘 小心翼翼 嘟囔 嫌弃 以上 发育
闪烁 好歹 退役 联赛 元素 拉扯 提示 后排 点燃 摄影 抽签 胡萝卜
替补 观众席 媳妇 理所当然 开幕 一幕 节奏 逐渐 名额 过于 灵活 质疑
版本 总结 如今 落后 复活 握手 爆发 占据 素质 官方 正面 当前
