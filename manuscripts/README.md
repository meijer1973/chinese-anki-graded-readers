# Manuscripts

Canonical manuscript source is stored as space-tokenized Chinese in:

```text
manuscripts/<slug>/chapters/*.zh-tok.txt
```

Generated EPUB folders are ignored by Git. Rebuild EPUB output with `scripts/build_epub.py` after validation and lead quality approval.

## Series Manuscripts

| Slug | Title | Status | Notes |
|---|---|---|---|
| `shanghai-rain-gate-crime` | `上海雨票案` | PASS | First 林安 journalist urban-fantasy crime manuscript. Read `series/an-lin/` before planning sequels. |
| `shanghai-spirit-lamp-case` | `上海灵灯案` | PASS | Second 林安 journalist urban-fantasy crime manuscript. Revalidated locally after writer-agent import. |

## Fixtures And Trials

| Slug | Purpose |
|---|---|
| `sample-known-words` | Tiny pipeline fixture. |
| `stretch-layer-fixture` | Layered vocabulary validation fixture. |
| `shanghai-rain-ticket` | Short story-first trial for the loosened unknown-token policy. |
