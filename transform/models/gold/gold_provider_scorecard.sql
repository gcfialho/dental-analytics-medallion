-- Provider x age group scorecard.
--
-- Preventive coverage (share of a provider's patients who received a preventive
-- service) is noisy for small practices: 3 of 3 patients is "100%". We apply
-- empirical-Bayes beta-binomial shrinkage per age group, so small practices are
-- pulled toward the group mean and rankings reflect evidence, not luck.
--
-- Services per patient gets a robust outlier flag (modified z-score on median/MAD),
-- a common screen for unusual billing intensity. It is a prompt for review, not a verdict.

with provider_age as (

    select
        rendering_npi,
        age_group,
        count(*)                                                                      as provider_rows,
        bool_or(adv_users_suppressed)                                                 as has_suppressed_rows,
        sum(adv_users)                                                                as patients_observed,
        sum(adv_users) filter (where prev_users is not null and adv_users is not null) as coverage_patients,
        sum(prev_users) filter (where prev_users is not null and adv_users is not null) as preventive_patients,
        sum(adv_users) filter (where adv_services is not null and adv_users is not null) as intensity_patients,
        sum(adv_services) filter (where adv_services is not null and adv_users is not null) as intensity_services
    from {{ ref('silver_provider_utilization') }}
    group by rendering_npi, age_group

),

rates as (

    select
        *,
        {{ safe_divide('preventive_patients', 'coverage_patients') }} as raw_preventive_coverage,
        {{ safe_divide('intensity_services', 'intensity_patients') }} as services_per_patient
    from provider_age

),

-- Method-of-moments prior. Between-provider variance = observed variance minus the
-- average binomial sampling variance; this avoids over-shrinking.
prior_moments as (

    select
        age_group,
        avg(raw_preventive_coverage)                                               as prior_mean,
        var_samp(raw_preventive_coverage)
            - avg(raw_preventive_coverage * (1 - raw_preventive_coverage) / coverage_patients)
                                                                                   as between_variance
    from rates
    where coverage_patients > 0
    group by age_group

),

prior as (

    select
        age_group,
        prior_mean,
        greatest(prior_mean * (1 - prior_mean) / nullif(between_variance, 0) - 1, 1) as prior_strength
    from prior_moments

),

intensity_center as (

    select age_group, median(services_per_patient) as median_spp
    from rates
    where services_per_patient is not null
    group by age_group

),

intensity_spread as (

    select r.age_group, c.median_spp, median(abs(r.services_per_patient - c.median_spp)) as mad_spp
    from rates as r
    inner join intensity_center as c using (age_group)
    where r.services_per_patient is not null
    group by r.age_group, c.median_spp

),

scored as (

    select
        r.*,
        p.prior_mean,
        p.prior_strength,
        (r.preventive_patients + p.prior_mean * p.prior_strength)
            / (r.coverage_patients + p.prior_strength)                             as shrunk_preventive_coverage,
        0.6745 * (r.services_per_patient - s.median_spp) / nullif(s.mad_spp, 0)    as services_per_patient_robust_z
    from rates as r
    inner join prior as p using (age_group)
    inner join intensity_spread as s using (age_group)
    where r.coverage_patients > 0

)

select
    md5(concat_ws('|', s.rendering_npi, s.age_group))                              as scorecard_key,
    s.rendering_npi,
    pr.provider_name,
    s.age_group,
    s.provider_rows,
    s.has_suppressed_rows,
    s.patients_observed,
    s.coverage_patients,
    s.preventive_patients,
    s.raw_preventive_coverage,
    s.shrunk_preventive_coverage,
    s.prior_mean                                                                    as age_group_prior_mean,
    s.prior_strength                                                                as age_group_prior_strength,
    rank() over (partition by s.age_group order by s.shrunk_preventive_coverage desc) as preventive_rank,
    s.services_per_patient,
    s.services_per_patient_robust_z,
    abs(s.services_per_patient_robust_z) > 3.5                                      as is_intensity_outlier
from scored as s
inner join {{ ref('silver_providers') }} as pr using (rendering_npi)
