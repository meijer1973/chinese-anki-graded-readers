# GitHub Agent Entry - Chinese Anki And Graded Readers

This repository contains two connected systems:

1. Chinese vocabulary Anki deck tooling.
2. A controlled-vocabulary Chinese graded-reader fiction pipeline.

It is intended to be readable by humans and remote coding/research agents working from GitHub.

## Initial Search Instruction

Content map of this repository:

https://raw.githubusercontent.com/meijer1973/chinese-anki-graded-readers/main/RESEARCH_AGENT_MAP.md

Read that file first for repository access, exact paths, raw URLs, and task routing. If fetching fails, report it to the user. If the remote repository appears stale or behind local work, report that so the team can push the latest information.

## Start Here

| Question type | Inspect first |
|---|---|
| How should agents work in this repo? | `AGENTS.md` |
| What is the high-level project? | `README.md` |
| How should remote agents traverse the repo? | `RESEARCH_AGENT_MAP.md` |
| What prompt should a remote research agent use? | `RESEARCH_AGENT_PROMPT.md` |
| What machine-readable manifest describes the repo? | `repo_manifest.json` |
| How is a known-word list generated? | `High frequency words 0-10000.txt`, `scripts/sync_known_words.py`, `data/known_words.metadata.json` |
| How is a chapter validated? | `scripts/validate_chapter.py`, `scripts/novel_tools.py` |
| How is a whole manuscript validated? | `scripts/validate_book.py`, `scripts/generate_reports.py` |
| How is quality reviewed? | `docs/quality-review.md`, `.agents/skills/chinese-lead-quality-review/SKILL.md` |
| How is series memory updated after an accepted story? | `docs/series-memory.md`, `scripts/check_series_memory_update.py` |
| How is EPUB built? | `scripts/build_epub.py`, `.agents/skills/epub-export/SKILL.md` |
| How do stretch words flow toward Anki? | `docs/anki-integration.md`, `scripts/export_stretch_words_for_anki.py` |
| How is Anki new-card order kept mixed? | `docs/anki-integration.md`, `scripts/audit_anki_card_distribution.py`, `scripts/schedule_anki_learning_order.py` |
| What is the first series manuscript? | `manuscripts/shanghai-rain-gate-crime/` |
| What is the latest accepted 林安 manuscript? | `manuscripts/shanghai-mirror-street-case/` |
| What is the energy-policy long-read? | `manuscripts/china-energy-policy-hormuz-long-read/` |
| What is the current standalone story trial? | `manuscripts/shanghai-rain-ticket/` |
| What is the sword-sect fantasy series scaffold? | `series/broken-sword-gate/`, `manuscripts/broken-sword-gate-01-entering-the-mountain/` |

## Access Layer

Repository:

```text
https://github.com/meijer1973/chinese-anki-graded-readers
```

Raw base URL:

```text
https://raw.githubusercontent.com/meijer1973/chinese-anki-graded-readers/main/
```

Construct raw file URLs as:

```text
<raw_base_url><relative_path>
```

Example:

```text
AGENTS.md ->
https://raw.githubusercontent.com/meijer1973/chinese-anki-graded-readers/main/AGENTS.md
```

## Path Reliability

- Prefer exact paths from `RESEARCH_AGENT_MAP.md`, `AGENT_GITHUB_ENTRY.md`, or `repo_manifest.json`.
- Use `reports/github-agent-index.md` for existence checks.
- Use `reports/url-index.md` when an external agent cannot construct URLs from a base path.
- Use GitHub search mainly for discovery, then confirm through exact paths.
- Refresh the reports with `python scripts/build_agent_index.py` after path or workflow changes.
- After accepted tracked work is complete, commit and push the active branch to `origin` unless the user explicitly asks not to or Git/validation blocks publication.

## Common Mistakes

- Treating ignored Anki exports or backups as source of truth.
- Treating EPUB files as canonical story source. The canonical source is `chapters/*.zh-tok.txt`.
- Assuming validation quality equals literary quality.
- Missing the extensive-reading vocabulary gate: default validation requires at least 98% known tokens and at most 2% approved non-core tokens.
- Forgetting to pass stretch packs, `book_specific_words.txt`, and `proper_nouns.txt` when validating layered manuscripts.
- Forgetting `--known-character-compounds --known-character-compound-limit 500` for Marcel personalized manuscripts that use the high-frequency character-compound layer.
- Treating unknown-token allowance as a target. It is only breathing room.
- Planning a new 林安 sequel before the previous accepted story has updated `series/an-lin/series_update_log.md`.
- Leaving completed tracked work only in a local checkout. Remote writer agents read GitHub, so pushed commits are the handoff.
