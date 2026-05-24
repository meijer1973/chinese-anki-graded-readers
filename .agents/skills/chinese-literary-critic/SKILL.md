---
name: chinese-literary-critic
description: Strict literary criticism for restricted-vocabulary Chinese fiction. Use when Codex needs to judge whether a vocabulary-valid graded-reader manuscript is interesting, varied, scene-driven, emotionally alive, or too conservative and repetitive.
---

# Chinese Literary Critic

Review the manuscript as literature under constraint. Do not excuse weak writing because the vocabulary is restricted.

## Read First

- `novel_bible.md`
- `outline.md`
- `characters.md`
- `continuity_log.md`
- `vocabulary_report.json`
- `quality/vocabulary_usage_report.json`
- `quality/repeated_phrase_report.json`
- all `chapters/*.zh-tok.txt`

## Evaluate

- premise strength
- chapter hooks
- scene-level conflict
- character desire
- reversals or discoveries
- emotional movement
- pacing
- dialogue variety
- descriptive variety
- ending strength
- whether the reader has a reason to continue
- whether any passage exists only to increase length, coverage, or stretch-word exposure
- whether approved stretch words create real story value
- whether Shanghai/urban setting vocabulary creates stronger scenes rather than name-dropping
- whether professions and social roles shape behavior and plot
- whether low fantasy creates tension while staying simple enough for the target level
- for 林安 journalist/crime manuscripts, whether reporting work creates actual pressure rather than just labels
- whether interviews, sources, files, articles, witnesses, suspects, and publication choices affect the plot

Identify technically valid but boring passages, repetitive structures, flat chapters, filler, padding, and artificially narrow vocabulary use. Suggest improvements using concepts likely expressible inside the known-word list. Do not rewrite the whole book unless asked.

## Output

Write `manuscripts/<slug>/quality/literary_critic_report.md` with:

- score from 1 to 10
- pass, polish, or rebuild recommendation
- top 5 strengths
- top 10 problems
- chapter-by-chapter notes
- specific polish recommendations
- whether the manuscript is too conservative
- whether the manuscript is too repetitive
- whether vocabulary use feels artificially narrow
- whether fantasy terms are natural or confusing
- whether locations are meaningful or decorative
- whether stretch vocabulary is learnable through repetition
- whether journalism/crime terms are naturally repeated and story-useful
- whether any chapter appears padded for count-based targets
