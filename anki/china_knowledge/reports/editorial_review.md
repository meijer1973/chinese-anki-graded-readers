# China Knowledge Editorial Review

Review date: 2026-08-06

Canonical source: `anki/china_knowledge/china_knowledge_400.tsv`

Decision: PASS

## Scope

The review covered all 400 stable IDs and the exact 65 geography, 90 history, 35 government, 55 economy, 40 society, 45 culture, 25 language, and 45 science/technology/environment distribution.

Each row has independently written Chinese and English questions, short answers, explanations, taxonomy, one or more source-catalog IDs, a source date, and a fact-check date. Every cited ID resolves to the 39-entry HTTPS source catalog. The source mix prioritizes primary government or institutional material and established international or museum references; it does not use copied study-card text.

## Bilingual Review

- All 400 rows have both-language questions, answers, and explanations.
- Digits in paired questions and answers were compared mechanically after normalization; there are no unresolved numeric mismatches.
- Exact and high-similarity question checks found no unresolved duplicates in either language.
- Chinese and English short answers were reviewed for the same claim scope rather than word-for-word phrasing.
- Dates with different normal written order use an unambiguous numeric or natural-language form on both sides.

## Factual and Framing Review

- Geography separates physical facts, administrative classifications, cities, and regional patterns. The province-count item explicitly uses the PRC official administrative convention rather than presenting a disputed territorial claim as universally agreed.
- History uses period and significance questions as well as dates. Multi-stage developments such as papermaking, printing, gunpowder, the compass, and political transitions avoid single-person or single-moment myths.
- Government distinguishes Party and state bodies, describes formal constitutional structure separately from political practice, and avoids implying that one institution explains the entire system.
- Economy distinguishes market activity from state influence and presents reform, trade, infrastructure, property, debt, regional, and industrial-policy claims with qualifications rather than fixed slogans.
- Society and culture include regional, generational, ethnic, and household variation. Terms such as `面子`, `关系`, filial piety, festivals, food, work culture, and family practice are not presented as universal behaviour.
- Language distinguishes Putonghua, regional varieties, spoken mutual intelligibility, shared writing, scripts, Pinyin, character structure, grammar, and naming conventions.
- Science, technology, energy, and environment cards separate capacity from output, reserves from processing, infrastructure benefits from trade-offs, and rapid clean-technology growth from the scale of coal and total energy demand.

## Volatile Claims

Sixteen rows contain explicit `as_of::*` tags. Other contemporary rows were phrased as durable institutional roles, mechanisms, or trends instead of point-in-time rankings and counts. `Source Date` and `Fact Checked` make later refreshes auditable.

## Automated Evidence

`scripts/china_knowledge/validate_china_knowledge.py` reports:

- status `PASS`;
- 400 notes and exact category targets;
- 400 bilingual explanations;
- zero missing source dates;
- zero validation failures;
- zero warnings;
- zero duplicate or near-duplicate question pairs;
- zero bilingual number warnings.

The representative sixteen-note fixture covers every category. The fake-Anki integration tests additionally prove one card per note, deterministic stable-ID updates, repeat-run idempotency, a dedicated five-new-cards preset, and unchanged Default/Chinese, Hindi, and Spanish resources.
