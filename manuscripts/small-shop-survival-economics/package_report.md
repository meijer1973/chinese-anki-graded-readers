# Package report — 小店怎么活下来

- Generated at: 2026-05-25T12:22:08Z
- Manuscript path: `manuscripts/small-shop-survival-economics/`
- EPUB path: `manuscripts/small-shop-survival-economics/epub/small-shop-survival-economics.epub`
- Chapter count: 16
- Total word-token count: 4890
- Unique used words: 544
- Unknown-token count: 0
- Forbidden unknown tokens over configured per-chapter limit: 0
- Business/economics stretch token count: 714
- Unique approved stretch words used: 82
- Quality review decision: PASS
- EPUB build succeeded: True

## Topic

A standalone, case-based nonfiction reader about how a small Shanghai shop survives. It introduces business/economics concepts through concrete repeated shop actions: income, expenses, price, cost, profit, customer trust, inventory, competition, scarcity, loans, tax, policy, sales, consumption, and production.

## Validation command recorded

```powershell
python scripts/validate_book.py `
  --known data/known_words.txt `
  --chapters manuscripts/small-shop-survival-economics/chapters `
  --out manuscripts/small-shop-survival-economics/vocabulary_report.json `
  --general-fiction-pack data/stretch_packs/general_fiction_100.txt `
  --setting-pack data/stretch_packs/shanghai_setting_150.txt `
  --profession-pack data/stretch_packs/professions_social_roles_100.txt `
  --urban-objects-pack data/stretch_packs/urban_objects_100.txt `
  --extra-pack data/stretch_packs/business_economics_60.txt `
  --book-specific manuscripts/small-shop-survival-economics/book_specific_words.txt `
  --proper-nouns manuscripts/small-shop-survival-economics/proper_nouns.txt
```
