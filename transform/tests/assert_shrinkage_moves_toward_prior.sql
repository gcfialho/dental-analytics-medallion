-- Empirical-Bayes estimates must lie between the raw rate and the prior mean.
select scorecard_key
from {{ ref('gold_provider_scorecard') }}
where shrunk_preventive_coverage
      < least(raw_preventive_coverage, age_group_prior_mean) - 1e-9
   or shrunk_preventive_coverage
      > greatest(raw_preventive_coverage, age_group_prior_mean) + 1e-9
