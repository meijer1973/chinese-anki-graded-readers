# Manuscripts

Canonical manuscript source is stored as space-tokenized Chinese in:

```text
manuscripts/<slug>/chapters/*.zh-tok.txt
```

Final EPUB files and build reports under `manuscripts/<slug>/epub/` are tracked for accepted manuscripts. Rebuild EPUB output with `scripts/build_epub.py` after validation and lead quality approval. For series manuscripts, update the living series memory package and verify it with `scripts/check_series_memory_update.py` before planning the next book.

## Series Manuscripts

| Slug | Title | Status | Notes |
|---|---|---|---|
| `shanghai-rain-gate-crime` | `上海雨票案` | PASS | First 林安 journalist urban-fantasy crime manuscript. Read `series/an-lin/` before planning sequels. |
| `shanghai-spirit-lamp-case` | `上海灵灯案` | PASS | Second 林安 journalist urban-fantasy crime manuscript. Revalidated locally after writer-agent import. |
| `shanghai-shadow-bridge-case` | `上海影子桥案` | PASS | Third 林安 journalist urban-fantasy crime manuscript. Revalidated locally after writer-agent import. |
| `shanghai-midnight-ringtone-case` | `上海零点铃声案` | PASS | Fourth 林安 journalist urban-fantasy crime manuscript. Revalidated locally after writer-agent import. |
| `shanghai-still-water-list-case-revised` | `上海静水名单案` | PASS | Revised fifth 林安 manuscript. Revalidated locally after writer-agent import and repaired into 13 story chapters. |
| `shanghai-lost-property-locker-case` | `上海失物柜案` | PASS | Sixth 林安 journalist urban-fantasy crime manuscript. Revalidated locally after writer-agent import. |
| `shanghai-silent-archive-case` | `上海无声档案案` | PASS | Seventh 林安 journalist urban-fantasy crime manuscript. Revalidated locally after writer-agent import. |
| `shanghai-old-city-gate-case` | `上海旧城门案` | PASS | Eighth 林安 journalist urban-fantasy crime manuscript. Imported from writer agent, retokenized/revalidated locally, and series memory updated. |

## Fixtures And Trials

| Slug | Purpose |
|---|---|
| `sample-known-words` | Tiny pipeline fixture. |
| `stretch-layer-fixture` | Layered vocabulary validation fixture. |
| `shanghai-rain-ticket` | Short story-first trial for the loosened unknown-token policy. |
