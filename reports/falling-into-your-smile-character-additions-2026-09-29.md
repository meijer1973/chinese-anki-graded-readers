# Falling Into Your Smile: 81 character notes

The user approved creation of the 81 missing single-character notes from the
99% character-coverage audit. All 81 were absent from the live Chinese Vocabulary
model and ranked source immediately before import.

## Applied and verified

- Added 81 notes and 162 cards through the guarded ordinary-word importer.
- All 81 new Word Recognition cards are active, new, and unstudied.
- All 81 new Sentence Recognition cards are suspended, new, and unstudied.
- Curated concise meanings, original example sentences, English translations,
  and sentence pronunciation. Added common headword pronunciation overrides
  where dictionary ordering favored rare senses.
- Appended the characters at source ranks 4589–4669. Rebuilding leaves all
  previous 4,588 TSV rows unchanged.
- Verified all 4,786 previous Chinese notes and all 9,972 previous collection
  cards are unchanged, excluding dynamic rendered scheduling predictions.
- No global learning-order change was applied. The character-closure check
  found no additional missing characters and added no further notes.
- Refreshed the live inventory: 4,867 Chinese notes, 9,734 Chinese cards,
  4,867 unique Word fields, and no duplicate words.
- Normal Anki sync succeeded after import.

The 81 characters add 11,991 covered occurrences in the previously audited
book, increasing coverage from 595,091 / 613,213 (97.044746%) to
607,082 / 613,213 (99.000184%). This measures presence of dedicated character
word cards, including suspended cards, rather than mastery or active-card-only
coverage. It excludes punctuation, Latin letters, digits, and navigation text.

## Subdeck routing status

Pending: the new cards remain temporarily in Default. The Windows computer-use
tool twice reported `failed to activate captured window`; the subsequently
opened Anki browser exposed accessibility text but a black screenshot.
The user has been asked to bring Anki to the foreground. No deck moves have
been attempted without the required full collection backup and restore test.

Once the window is accessible, finish the standard backup, restore verification,
trial, repeat, and live routing procedure in `docs/chinese-subdecks-fsrs.md`.
The prepared plan is exactly 81 word cards to `Default::Single characters`
and 81 sentence cards to `Default::Sentences`, preserving their queue states.

## Verification and retained local artifacts

- `python build_anki_chinese.py`: 4,669 rows; zero unreviewed meanings and zero
  generated placeholder examples.
- `python ensure_single_character_notes.py`: zero missing components and zero
  added notes; only a local learning-order plan was generated.
- Repository syntax check passed.
- `python -m unittest tests.test_add_chinese_words_to_anki tests.test_export_current_anki_words`:
  12 tests passed.
- `git diff --check`: passed.

Private import manifests, before/after snapshots, exact new IDs, and the
pre-import scheduled deck backup remain under ignored
`anki/first_frost/local_results/smile_81_additions_20260929/`.
The deck backup is an `.apkg`; it is not used as a substitute for the full
`.colpkg` required before subdeck routing. Prepared routing helpers remain in
the local Downloads folder `Anki-smile-81-routing-20260929`.

## Added characters, in book-frequency order

谣 岳 辅 摁 嚷 贪 纷 抖 懵 掏 捂 掀 艹 拎 璐 御 嘟 眨 囔 揉 瞳 噔 咔 帖 蹦 咋 腕 哒 绷 虾
怼 飘 瘫 咦 嚓 捧 丛 褐 硕 爪 嗤 摘 胀 遮 昆 翘 茸 哐 桓 哑 蝶 蹙 膨 蝴 踹 挠 珏 叨 捞 雀
勺 呜 茫 唧 掰 躁 豹 嗷 惦 瓣 泛 锤 咳 嘎 皎 盲 粥 谐 逆 颤 串
