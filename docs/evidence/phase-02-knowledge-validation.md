# Phase 02 Knowledge Validation

- Status: `PASS`
- Generated: `2026-08-22T17:56:18.116370+08:00`

## Counts

- pages: 18
- chunks: 67
- food_facts: 31
- plan_rules: 37
- platform_facts: 12
- unknown_glyph_pages: 6
- unknown_glyph_chunks: 8
- verified_records: 7
- review_required_records: 73

## Runtime gates

- file_validation: `PASS`
- database_migration: `PASS`
- embedding_index: `PASS`
- unknown_glyph_exclusion: `PASS`
- core_recommendation_review: `PASS`
- remaining_structured_records: `QUARANTINED_REVIEW_REQUIRED`
- second_person_review: `PARTIAL_CORE_RELEASED`

## Errors

- None

## Warnings

- 6 pages / 8 chunks contain source-level unknown glyphs; affected rules remain review_required.
- 7 core recommendation rules completed the authorized assisted review and are released to the deterministic engine.
- 73 remaining structured records still require participant second-person review and remain quarantined from deterministic recommendations.
- Unknown-glyph runtime exclusion: PASS.
- Database migration execution: PASS.
- Embedding/vector build: PASS.
