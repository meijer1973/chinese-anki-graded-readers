---
name: chinese-prose-variety-polish
description: Polish restricted-vocabulary Chinese manuscripts for prose variety, rhythm, repeated dialogue tags, repeated sentence frames, and flat exposition while preserving validation.
---

# Chinese Prose Variety Polish

Use this after vocabulary validation and before final lead approval. The goal is not to make the text harder. The goal is to make a valid graded reader feel more like a real story.

## Read First

- `docs/style-bank-controlled-chinese.md`
- `manuscripts/<slug>/vocabulary_report.json`
- `manuscripts/<slug>/quality/repeated_phrase_report.json`
- `manuscripts/<slug>/quality/prose_variety_report.json`
- `manuscripts/<slug>/continuity_log.md`
- the canonical `chapters/*.zh-tok.txt`

For 林安 sequels, also read `series/an-lin/series_bible.md`, `series/an-lin/chronology.md`, and `series/an-lin/sequel_constraints.md`.

## Responsibilities

- Reduce visible `X 说` repetition.
- Reduce repeated sentence openings, repeated endings, and mechanical phrase frames.
- Replace flat exposition with small action, reaction, object handling, setting movement, or emotional consequence.
- Make sure every change still uses exact core known, configured personal-known, stretch, book-specific, proper-noun, or intentionally budgeted unknown tokens.
- Preserve plot facts, chronology, and character continuity.
- Do not pad chapters or add decorative stretch words.

## Process

1. Run or read:

```powershell
python scripts/prose_variety_report.py --chapters manuscripts/<slug>/chapters --out manuscripts/<slug>/quality/prose_variety_report.json
```

2. Identify the worst 3-10 repeated frames.
3. Edit only the sentences or passages that need style repair.
4. Revalidate each touched chapter.
5. Re-run `scripts/prose_variety_report.py`.
6. Update `quality/prose_variety_polish_report.md` with:
   - frames repaired;
   - chapters touched;
   - validation command run;
   - any remaining style risks.

## Guardrails

- Do not use a synonym unless the exact token is allowed.
- Do not remove useful learning repetition.
- Do not make a simple sentence obscure merely to avoid `说`.
- Do not change the story event unless the lead reviewer requested a rewrite.
- If a repeated phrase is a deliberate motif, document that rather than rewriting it.
