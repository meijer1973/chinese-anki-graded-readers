# Falling Into Your Smile: 60 character additions

Added all 60 characters from the user's
`falling_into_your_smile_missing_anki_top1800.csv` attachment on 17 October 2026.
The CSV was used as a character selection; its novel-frequency and coverage
figures were not recalculated or treated as deck instructions. All 60 characters
were absent from the live Chinese Vocabulary note type at preflight.

| Verified result | Count |
| --- | ---: |
| New notes | 60 |
| New active Word Recognition cards | 60 |
| New suspended Sentence Recognition cards | 60 |
| Total single-character Word Recognition cards | 2,528 |
| Total Chinese Vocabulary notes | 5,058 |
| Duplicate Chinese headwords | 0 |
| Active new cards mixed | 470 |

## Content

Appended the selected characters in attachment order to the ranked source,
preserving all 4,800 preceding source rows. The source now has 4,860 rows.
Added concise meanings, common readings, original example sentences, English
translations and reviewed sentence pinyin. Polyphonic readings were chosen in
context, including 扒、撩、撇、扛、涨、揣、衩 and 吁. Local CC-CEDICT entries
were consulted during curation.

The builder regenerated both TSV exports. Every new study field matched its
curated source, every old exported row was unchanged, and no row used a generated
placeholder or required meaning review. Character closure found no additional
missing component characters.

## Card states, routing and learning order

The guarded importer passed duplicate and canAddNotes checks and created exactly
60 notes. Only the new sentence cards were suspended. Import verification
preserved all 4,998 preceding Chinese notes and all 10,396 preceding collection
cards.

Full media-inclusive collection backups passed isolated native Anki restore
checks before import and routing. The collection's media manifest was empty.
Routing passed a dry run, an isolated-copy application and a no-op repeat before
live execution through AnkiConnect's native Card API wrapper. Read-only SQLite
copies were made while User 1 was closed in the GUI; no live SQL writes were used.

The 60 word cards now belong to `Default::Single characters`, and their 60
sentence siblings belong to `Default::Sentences`. Default remains an empty
combined parent. Raw routing verification checked all 10,516 collection cards,
preserved all 21,258 review entries, and preserved stored memory state, schedules,
notes, models and settings except the intended deck membership changes.

The 60 new word cards were shuffled and distributed through the 470 active new
cards: 15 additions in each quarter of the queue. Before/after verification
checked all cards and 5,058 Chinese notes, with no unexpected changes. Suspended
cards and existing review schedules were preserved. Ascending position gathering,
the combined 10-new-card daily limit and deck retention overrides were preserved.
Anki synchronization and final live checks completed successfully.

## Validation and audit

- `python build_anki_chinese.py`
- `python ensure_single_character_notes.py`: no missing characters or extra notes.
- Python syntax checks for the three edited content files.
- Guarded import dry run and post-import field/state comparison.
- Native full-backup restore, routing trial and raw-state preservation checks.
- Active new-card membership, ordering and state-preservation checks.
- `python scripts/export_current_anki_words.py`: 5,058 unique headwords, no duplicates.
- `git diff --check`.

Private input, backups, card manifests and verification reports remain in ignored
`anki/first_frost/local_results/smile_60_additions_20261017/`.
The graded-reader vocabulary policy and allowlists were not expanded.

## Added characters

嗖 嘶 扒 咕 僧 嗅 烁 躬 鞠 撩 芒 颊 宵 岚 峡 搓 撇 歹 萌 踮
凳 嗳 戳 敛 耸 蹿 捶 狸 砰 伐 喵 噜 腻 译 漉 绵 赅 颚 叼 叽
咸 扛 揪 涨 猝 膛 晰 曜 衩 巅 揣 吁 葱 驳 崽 焉 窜 黏 亦 届
