---
name: chinese-normal-reader-review
description: Normal-reader review for restricted-vocabulary Chinese fiction. Use when Codex needs a blunt learner-reader reaction about whether a manuscript is boring, confusing, engaging, repetitive, natural, or worth continuing.
---

# Chinese Normal Reader Review

Read like a real learner-reader, not a technical validator and not a literary theorist. Do not overpraise because the task is hard.

## Read First

- all `chapters/*.zh-tok.txt`
- `novel_bible.md` and `outline.md` only for context after first-pass reading
- quality evidence reports if needed

## Evaluate

- Did I want to continue?
- Did I understand what was happening?
- Did I care about the characters?
- Did chapters feel different from each other?
- Was there too much repeated dialogue?
- Did the ending satisfy something?
- Did the restricted vocabulary feel natural or mechanical?
- Did the city feel alive?
- Did characters feel different from each other?
- Was the fantasy element interesting?
- Did stretch words make the story too hard?
- Were locations meaningful, or just names?

Be blunt about whether the book feels like a real story.

## Output

Write `manuscripts/<slug>/quality/normal_reader_report.md` with:

- score from 1 to 10
- pass, polish, or rebuild recommendation
- boredom points
- confusing points
- favorite moments
- least interesting chapters
- whether the reader would continue after chapter 1
- whether the reader would finish the book
- whether stretch vocabulary helped or hurt the reading experience
