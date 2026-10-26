# Benchmark scoring plan (fixed 2026-10-12, before any adjudicator output was seen)

- Items: 400 (200 true matches, 200 true non-matches), benchmark_items.json, SHA-256 in benchmark_meta.json.
- Each adjudicator (Claude Opus 5.5, Claude Sonnet 5.5) judges all 400 items in two batches of 200
  (fresh session per batch, identical instructions adjudicator_instructions_v1.md), with no access to the answers.
- Decision mapping: "match" = linked; "non-match" and "uncertain" = not linked (same rule as the real run).
  Uncertain rates are reported separately.
- Sensitivity = linked true matches / 200; specificity = not-linked true non-matches / 200; Wilson 95% CIs.
- Acceptance (protocol Section 6): an adjudicator is accepted only if both point estimates are >= 0.95.
- Final (consensus) decision as in the real run: agreement stands; disagreements go to Claude Fable 5.1,
  which sees both reasons. Consensus sensitivity and specificity are also reported.
- Agreement: Cohen's kappa between the two adjudicators (3 categories and collapsed to linked / not linked),
  with a bootstrap 95% CI (2,000 resamples, seed 20261012).
- Missing or unparseable answers count as errors (a missing answer on a true match = missed; on a true
  non-match = not linked, but reported).
- Breakdown by difficulty (institution variant, name variant, same first name) is descriptive only.
