# Repair Report - 上海静水名单案

## Diagnosis
The 74-chapter version was structurally wrong. The repository does not require microchapters. The bad structure came from a generation/package error: each scene beat was promoted into a chapter because the workflow requires chapter-level planning and validation. That made the validation surface look orderly but produced chapters averaging only 96.7 word tokens.

## Repair
This revised package merges the 74 microchapters into 13 story chapters. The underlying story text is preserved; chapter boundaries, outline, planning files, reports, and EPUB navigation are corrected.

## Result
- Original: 74 chapters, 7156 word tokens, average 96.7 tokens/chapter.
- Revised: 13 chapters, 7156 word tokens, average 550.5 tokens/chapter.
- Vocabulary content: unchanged.
- Unknown tokens: 0.
- EPUB: rebuilt.

## Repository fix needed
Add a chapter-structure diagnostic to the quality gate. It should not impose a hard universal chapter length, but it should warn or block when a manuscript has many microchapters unless `microchapter_mode` is explicitly declared and justified.

## Local import note
During repository import, retained source tokens that were outside the current core, Marcel personal-known, and stretch layers were made explicit in `book_specific_words.txt`. This keeps the text unchanged while making every non-core token auditable under the current validator.
