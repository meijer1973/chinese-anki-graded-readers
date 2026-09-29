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

## Completed subdeck routing

After restoring access to Anki's window, completed the full backup, isolated
restore verification, dry run, trial move, no-op repeat, live dry run, and live
move from `docs/chinese-subdecks-fsrs.md`. All verification reports passed.

- Moved 81 active word cards to `Default::Single characters`: **2,337 total**.
- Moved 81 suspended sentence cards to `Default::Sentences`: **4,867 total**.
- `Default::Multi-character words` remains at **2,530 cards**.
- Default has no cards directly in the parent after routing.
- Preserved all 10,134 collection cards' scheduling and memory state, all
  17,504 review-log entries, and the existing note contents and deck settings.
- Verified the 81 word cards remain active and all 81 sentence siblings remain
  suspended. Normal sync succeeded after routing.

Full collection backup, with Include media enabled:
`C:\Users\meije\Downloads\Anki-smile-81-routing-20260929\collection-before-routing-20260929.colpkg`.
Size: 1,624,663 bytes. SHA-256:
`6e6df29e1da46807563c0306a03997ddd9d423403269aa8e02254268fecdb4e7`.
The media manifest was empty. The separate restore-test profile has no sync
credentials. Private restore evidence and trial/live manifests remain beside
the full backup.

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
The pre-import deck backup is an `.apkg`; it was not used as a substitute for
the full `.colpkg` verified before subdeck routing. Routing helpers and full
backup evidence remain in the local Downloads folder
`Anki-smile-81-routing-20260929`.

## Added characters, in book-frequency order

谣 岳 辅 摁 嚷 贪 纷 抖 懵 掏 捂 掀 艹 拎 璐 御 嘟 眨 囔 揉 瞳 噔 咔 帖 蹦 咋 腕 哒 绷 虾
怼 飘 瘫 咦 嚓 捧 丛 褐 硕 爪 嗤 摘 胀 遮 昆 翘 茸 哐 桓 哑 蝶 蹙 膨 蝴 踹 挠 珏 叨 捞 雀
勺 呜 茫 唧 掰 躁 豹 嗷 惦 瓣 泛 锤 咳 嘎 皎 盲 粥 谐 逆 颤 串
