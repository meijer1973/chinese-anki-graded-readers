# Completion Response Template

Use this final-response shape when delivering a completed graded-reader book, EPUB, source package, or validation-ready manuscript. Keep the response concise, structured, and evidence-backed. Do not bury validation status in prose.

## Standard Shape

```markdown
Completed Book <number or slug>: **<Chinese title>**.

Files:

[Download/Open the EPUB](<epub path or sandbox link>)

[Download/Open the source and manuscript package](<zip path or manuscript folder>)

I checked the current repository rules before building it. The active known-word file is generated from `High frequency words 0-10000.txt`; the active known-word count is **<known_word_count>**. <Vocabulary profile sentence.> The extensive-reading gate remains **>=98% known tokens** and **<=2% approved non-core tokens**, with canonical manuscript text in space-tokenized `chapters/*.zh-tok.txt`.

| Item | Result |
| --- | ---: |
| Title | <title> |
| Series | <series or standalone> |
| Topic | <topic or premise> |
| Chapter count | <n> |
| Total word tokens | <n> |
| Unique used words | <n> |
| Vocabulary profile | <public / Marcel personalized / other> |
| Known-word baseline | <n> |
| Character-compound limit | <n or not used> |
| Known-token coverage | <percent> |
| Approved non-core percentage | <percent> |
| Forbidden unknown tokens | <n> |
| Forbidden unknowns over chapter limit | <n> |
| Validation command | `<command or report path>` |
| Lead quality decision | <PASS / not run / blocked> |
| EPUB structural check | <PASS / not built / blocked> |

<One short paragraph summarizing the book's actual content, structure, and reader value.>

<For nonfiction/current topics only: summarize the factual frame and cite sources. If browsing or source access was unavailable, say that plainly. For fiction, summarize the story arc instead.>

The source package includes <canonical tokenized chapters, natural reading copy, chapter vocabulary plans, vocabulary report JSON, per-chapter validation JSON, used word lists by layer, quality reports, EPUB build tree, build report, etc.>

Limitations: <state any nonstandard validation, missing repo commit, unavailable source access, skipped review, or local-only artifact. If there are no material limitations, say "No material limitations beyond the normal repo validation constraints.">
```

## Required Reporting Rules

- Start with the delivered object: book number/slug and title.
- Put files or paths immediately after the opening line.
- Include a metrics table for every completed book or EPUB.
- Report the active known-word baseline, currently from `data/known_words.metadata.json`.
- Report vocabulary profile and learner-profile layers when used.
- Report known-token coverage and approved non-core/stretch percentage.
- Report forbidden unknown tokens and forbidden unknowns over the configured per-chapter limit.
- Report the validation command run, or the exact validation report path when a remote/sandbox agent cannot run the command directly.
- Report lead quality decision and EPUB structural check separately.
- Mention canonical source location: `manuscripts/<slug>/chapters/*.zh-tok.txt`.
- For current nonfiction, use dated external sources and cite them. If the agent could not browse or fetch sources, say so in the limitations section.
- If the work was not committed or pushed when repo policy requires it, say that explicitly.

## Paths And Links

- In local Codex, use repository paths such as `manuscripts/<slug>/epub/<slug>.epub`.
- In sandboxed remote environments, use sandbox download links when available.
- If both are available, include both only when useful; avoid clutter.
- Do not imply that an EPUB exists when only manuscript planning files were created.

## Avoid

- Long unstructured narratives before the metrics.
- Saying only "validation passed" without the actual numbers.
- Omitting source package contents.
- Hiding blockers or skipped review steps.
- Treating vocabulary validation as a substitute for lead quality review.
