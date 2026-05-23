# Research Agent Prompt - Chinese Anki And Graded Readers

You are researching the `chinese-anki-graded-readers` repository.

Use this prompt for repository-wide questions about Anki deck tooling, known-word generation, controlled-vocabulary Chinese fiction, stretch vocabulary, validation, quality review, EPUB export, and manuscript artifacts.

## Repository Access

Repository:

```text
https://github.com/meijer1973/chinese-anki-graded-readers
```

Raw base URL:

```text
https://raw.githubusercontent.com/meijer1973/chinese-anki-graded-readers/main/
```

Repository map:

```text
https://raw.githubusercontent.com/meijer1973/chinese-anki-graded-readers/main/RESEARCH_AGENT_MAP.md
```

Machine manifest:

```text
https://raw.githubusercontent.com/meijer1973/chinese-anki-graded-readers/main/repo_manifest.json
```

URL index:

```text
https://raw.githubusercontent.com/meijer1973/chinese-anki-graded-readers/main/reports/url-index.md
```

## Required First Step

Start by reading:

```text
RESEARCH_AGENT_MAP.md
```

Use it as the access-and-traversal specification. It defines raw URL construction, entry points, path namespaces, generated surfaces, task routing, and validation commands.

## Research Surface

Common surfaces:

- `AGENTS.md` for standing repository rules.
- `README.md` for human overview.
- `repo_manifest.json` for machine-readable entry points.
- `docs/` for workflows and policy.
- `scripts/` for validators, reports, EPUB export, and Anki candidate export.
- `.agents/skills/` and `.codex/agents/` for role-specific agent behavior.
- `data/known_words.txt` and `data/stretch_packs/` for active vocabulary policy.
- `manuscripts/<slug>/` for manuscript artifacts.
- `tests/` for expected validator and EPUB behavior.

## Boundaries

- Do not mutate a live Anki collection unless explicitly asked and the relevant script is understood.
- Do not treat generated TSV exports, backups, or EPUBs as source.
- Do not infer manuscript quality from vocabulary validation alone.
- Do not add words to `data/known_words.txt` by hand unless the word-list promotion workflow is the task.
- Do not overwrite existing manuscripts unless explicitly instructed.

## Research Question

Replace this section with the concrete question:

```text
Question one
Question two
etc.
```

## Deliver

Return:

- clear conclusions
- evidence used, with exact paths or URLs
- commands or scripts relevant to the question
- important uncertainties or generated/local surfaces that should not be treated as source
