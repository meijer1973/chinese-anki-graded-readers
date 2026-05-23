---
name: chinese-lead-quality-review
description: Lead quality decision for restricted-vocabulary Chinese manuscripts. Use when Codex needs to combine validation, continuity, vocabulary breadth, literary critic, and normal reader reports into a final pass, polish, rewrite, or rebuild decision.
---

# Chinese Lead Quality Review

The lead reviewer can reject a vocabulary-valid book. Do not accept bland or repetitive work merely because it is mechanically correct.

## Read First

- `vocabulary_report.json`
- `continuity_log.md`
- `quality/vocabulary_usage_report.json`
- `quality/repeated_phrase_report.json`
- `quality/literary_critic_report.md`
- `quality/normal_reader_report.md`

## Decisions

Use one of:

- `PASS`
- `POLISH`
- `PARTIAL_REWRITE`
- `COMPLETE_REBUILD`

Recommend `PASS` only if validation has no chapter above the configured forbidden-unknown budget, continuity has no serious contradictions, literary critic score is at least 7, normal reader score is at least 7, and no chapter is clearly filler or padded. Unknowns within budget should be intentional, useful, and not confusing.

Recommend `POLISH` for local issues in a usable manuscript.

Recommend `PARTIAL_REWRITE` when some chapters work and some need substantial rewriting.

Recommend `COMPLETE_REBUILD` when the premise is dull, the whole book is repetitive, vocabulary use is severely narrow, the normal reader would not continue, several chapters are filler, or the book feels like a validation exercise.

Reject padding. Do not accept a chapter because it hits a token count, coverage target, or stretch-word exposure target. Counts are evidence only. A shorter complete chapter can pass; a longer padded chapter should fail.

For low-fantasy Shanghai manuscripts, reject or require rewrite when Shanghai words are decorative only, fantasy terms are confusing, professions do not affect character behavior, stretch words are dumped without repetition, the book remains bland despite broader vocabulary, or the text is too difficult for the configured target level.

## Output

Write `manuscripts/<slug>/quality/lead_quality_decision.md` with:

- final decision
- required next action
- reasons
- blocking issues
- non-blocking issues
- whether polish is allowed
- whether complete rebuild is required
- specific instructions for the next writer agent
- whether stretch vocabulary is approved, needs polish, or should be reduced
- whether the current EPUB build is allowed

EPUB export is allowed only when the file explicitly contains `Final decision: PASS`.
