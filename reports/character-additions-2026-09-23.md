# Character additions — 23 September 2026

Added the 32 explicitly requested characters, each absent from both the ranked
source and the live Chinese Vocabulary model:

豫 稀 僻 凿 删 吴 吼 呗 啃 啰 嗡 嗦 噗 嚏 塌 奢 寥 寺 屑 弊 彦 怂 恒 恤 惰 捏 掐 斤 斩 朕 梢 氛

The source entries were appended at positions 4406–4437 without reordering prior
entries. These positions are source ranks, not a new corpus-frequency estimate.
Concise meanings and original examples are retained in the existing override
files; contextual pinyin overrides cover ambiguous and neutral-tone readings.
TSV regeneration and character-closure checks passed, with no extra characters
needed and no placeholder examples in this batch.

The guarded importer passed its dry run and added 32 notes with duplicate
protection. Each has one active Word Recognition card in
`Default::Single characters` and one suspended Sentence Recognition card in
`Default::Sentences`. The new word cards were shuffled into the existing active
new-character queue, preserving the existing cards' relative order. No other
cards were activated or suspended, and no existing note fields were changed.

A media-inclusive full collection package was integrity-checked and restored
into a separate profile without sync credentials. The routing trial passed,
its repeat made no changes, and the live move passed complete card-state and
review-history preservation checks. The final verification confirmed all 32
word/sentence state pairs and the mixed order. Normal sync completed.
Private backups, card IDs, and detailed manifests remain outside Git.

The refreshed live-word inventory contains 4,635 unique Chinese notes and no
duplicate headwords. It remains an inventory, not a learner known-word list.

Definitions use the repository's CC-CEDICT dataset. Additional reading/sense
checks used Han Dian entries for [呗](https://www.zdic.net/hans/呗),
[啰](https://www.zdic.net/hans/啰), [凿](https://www.zdic.net/hans/凿),
[豫](https://www.zdic.net/hans/豫), [彦](https://www.zdic.net/hans/彦),
[怂](https://www.zdic.net/hans/怂), and [梢](https://www.zdic.net/hans/梢).
