# Data audit: what v1 got wrong and how v2 fixes it

v1 of this project (MySQL + hand-run SQL scripts + Streamlit) produced a dashboard and
an "AI report" that looked plausible. Re-reading the source data dictionary semantics
and profiling the CSV showed that several headline numbers were wrong. This page
documents each issue, the evidence, and the fix. Every fix is enforced by a dbt data
test or a pytest test, so it cannot silently regress.

| # | Issue in v1 | Evidence | Fix in v2 | Guarded by |
|---|---|---|---|---|
| 1 | **Double-counted services.** `total_services = ADV + PREV + TXMT + EXAM`. | PREV/TXMT/EXAM are subsets of ADV (annual dental visit = any dental service). In every row with published values, each category is ≤ ADV. | ADV is the total. Nothing is summed across categories. | `assert_category_counts_are_subsets_of_any_service`, `test_total_services_is_adv_not_a_sum_of_categories` |
| 2 | **Suppressed counts treated as 0.** `COALESCE(NULLIF(x, ''), '0')`. | 24% of rows have a blank patient count with annotation code 1. No published patient count falls between 1 and 10 (treatment and exam publish true zeros), consistent with small-cell suppression of values 1–10. Code 2 appears on service counts withheld so suppressed patient counts cannot be derived. | Suppressed values stay NULL with a `*_suppressed` flag. Rates use only rows where both sides are published. Patient totals are reported with lower/upper bounds. | `assert_suppression_is_explicit`, `assert_observed_patient_counts_above_suppression_threshold`, `test_suppressed_counts_are_null_not_zero` |
| 3 | **Duplicate rows.** | 505 rows repeat another row for the same NPI, delivery system, provider type and age group with identical metrics; only the spelling of the provider name differs (e.g. `IZRAYLEVICH NINA` vs `IZRAYLEVICH, NINA, DDS`). | Exact metric copies are dropped in silver. The 22 groups whose metrics genuinely differ are kept and flagged `has_name_variants`. A canonical name per NPI lives in `silver_providers`. | `assert_deduplication_only_drops_exact_metric_copies`, `test_silver_drops_only_name_spelling_duplicates` |
| 4 | **"System effectiveness score" measured size.** Score included `total_users / 1000`, so FFS "won" with 6449 points against single digits. | FFS has ~16x more provider-level patients than GMC and PHP combined. | Removed. Delivery systems are compared on interpretable rates (preventive/exam/treatment coverage, services per patient). | — |
| 5 | **"Provider efficiency score" was arbitrary and rewarded volume.** Weighted mix of services per user, preventive ratio, volume tiers and system count. | Weights had no justification. Higher services per user both raised the score and was described as "preventing overutilization". | Replaced with (a) empirical-Bayes shrunk preventive coverage, which ranks providers on evidence rather than luck, and (b) a robust median/MAD outlier flag for service intensity, framed as a review screen. | `assert_shrinkage_moves_toward_prior`, `test_shrinkage_pulls_small_practices_harder` |
| 6 | **Averages of ratios.** Segment rates were `AVG(row_ratio)`. | A practice with 11 patients weighed as much as one with 70,000. | Ratios of sums over published rows. | `test_segment_totals_match_program_kpis` |
| 7 | **"AI-generated insights" did not use AI.** | The dashboard called a template function. The OpenAI method was never invoked, used `gpt-3.5-turbo` and free-text output. | Real LLM call with structured outputs (Pydantic schema) over a curated fact sheet. Every number in the output is fact-checked against the gold layer before display. Rejected findings are shown, not hidden. | `test_guardrails.py`, `test_brief.py` |
| 8 | **"Patients" overstated.** Totals summed provider-level unique patients and called them patients served. | A beneficiary seen by two providers appears in both rows. | Labelled "provider-level patients" everywhere, with the caveat in the brief. | — |
| 9 | **Typing.** Counts stored as `VARCHAR` and summed implicitly; "ADV" documented as "Advantage". | Schema of v1 `trusted_dental`. | Typed `bigint` counts in silver; column docs follow the source definitions. | dbt schema tests |

## Headline numbers, v1 vs v2

| Metric | v1 | v2 |
|---|---|---|
| Total dental services | 71,211,862 | **42,560,256** |
| Services per patient | 10.41 | **6.34** |
| Provider-level patients | 6,842,769 (duplicates included, suppressed rows as 0) | **6,713,211** published; 6,718,962–6,770,721 including suppressed rows |
| Children vs adults, preventive care | "17.7% vs 9.0% of preventive services" (share of an inflated total) | **79.2% vs 47.5%** of patients received a preventive service |
| Best delivery system | FFS, "effectiveness score 6449.46" | No single score. FFS 67.6%, PHP 65.1%, GMC 56.4% preventive coverage |

v2 values were computed independently with the Python standard library from the raw
CSV and are pinned by the integration tests in `tests/test_warehouse.py`.
