# Package Report — 《中国能源为什么要变》

## Summary

- Slug: `china-energy-policy-hormuz-long-read`
- Type: standalone nonfiction / economic-news graded reader
- Topic: China energy policy, energy security, and the Strait of Hormuz shock
- Chapters: 33
- Raw space-token count: 4739
- Validator word-token count: 3945
- Lexical token count excluding punctuation and numeric tokens: 3940
- Unique validator tokens used: 751
- Unique lexical words used: 746
- Unknown-token count: 0
- Forbidden unknown tokens over per-chapter limit: 0
- Personal-known token count: 0
- High-frequency character-compound token count: 0
- Core known tokens: 2547
- Business/economics stretch tokens: 261
- Book-specific energy-policy tokens: 1132
- Proper-noun tokens: 5
- Stretch token percent: 35.44
- Book-specific energy-policy word-list entries: 390
- Proper-noun word-list entries: 9
- Quality review decision: PASS
- EPUB build: succeeded
- EPUB zip structure check: passed

## Vocabulary profile

Public graded-reader mode, using active core known words, approved business/economics stretch words, general fiction where useful, book-specific energy-policy terms, and listed proper nouns. No Marcel personal-known layer was used.

## Validation command intended for a local repository checkout

```powershell
python scripts/validate_book.py --known data/known_words.txt --chapters manuscripts/china-energy-policy-hormuz-long-read/chapters --out manuscripts/china-energy-policy-hormuz-long-read/vocabulary_report.json --general-fiction-pack data/stretch_packs/general_fiction_100.txt --extra-pack data/stretch_packs/business_economics_60.txt --book-specific manuscripts/china-energy-policy-hormuz-long-read/book_specific_words.txt --proper-nouns manuscripts/china-energy-policy-hormuz-long-read/proper_nouns.txt
```

## Local repository verification

This package was imported into the repository checkout and rerun with the local validation, report-generation, quality-gate, and EPUB-build scripts. The summary above reflects those local outputs.

## Files inside the manuscript package

- `chapters/*.zh-tok.txt` — canonical tokenized Chinese manuscript
- `chapters/*.validation.json` — chapter-level validation reports
- `planning/*_vocab_plan.md` — chapter vocabulary plans
- `book_specific_words.txt` — energy-policy topic layer
- `proper_nouns.txt` — listed proper nouns
- `vocabulary_report.json` — whole-book validation summary
- `reading_copy.md` — noncanonical natural reading copy
- `source_notes.md` — factual source basis
- `quality/*` — quality reports and lead decision
- `epub/china-energy-policy-hormuz-long-read.epub` — generated EPUB
- `epub/build_report.json` — EPUB build report
