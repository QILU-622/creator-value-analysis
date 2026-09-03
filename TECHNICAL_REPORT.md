# Technical Report: Creator Resource Reallocation

## 1. Project scope and ownership

This is an independent portfolio project. I designed the business question, synthetic dataset, metric framework, ranking logic, offline evaluation, and proposed experiment controls. No employer, client, platform, internship, or confidential data were used.

The synthetic data contain 18,742 creator profiles, more than 326,000 content-performance records, and weekly activity and incentive tables. Absolute values should not be interpreted as platform benchmarks.

## 2. Decision problem

A platform has limited traffic and cash incentives. The existing allocation rule may preserve historical exposure advantages even when those creators no longer produce the strongest retention or revenue per unit of support.

The decision is not “which creators look valuable?” It is: **which creators should enter a fixed-size high-resource pool, what evidence supports changing the rule, and what must still be tested online?**

## 3. Metric framework

| Layer | Metrics | Decision use |
|---|---|---|
| Primary outcomes | 30-day retention; revenue per unit of incentive | Test whether the selected pool sustains supply and produces more value per unit of support |
| Cost guardrail | Average cash incentive per selected creator | Prevent an efficiency claim from hiding higher support cost |
| Migration guardrail | Overlap between old and adjusted top-N lists | Measure operational disruption and review load |
| Diagnostic evidence | Exposure concentration; revenue concentration; creator segments | Locate misallocation and define targeted actions |
| Online risk controls | Complaints; fraud; safety; creator churn; SRM | Required before any real rollout decision |

## 4. Method

1. Filter to creators who completed a first publication.
2. Winsorise revenue per 1,000 exposures at the 1st and 99th percentiles.
3. Convert the old-rule score, retention, efficiency, and resource occupancy into percentile ranks.
4. Calculate the adjusted priority score:

```text
0.60 × old-rule percentile
+ 0.20 × retention percentile
+ 0.15 × efficiency percentile
+ 0.05 × low-resource-occupancy percentile
```

5. Select the top 4,200 creators under each rule.
6. Compare outcomes at the same pool size and inspect which segments enter and leave the list.
7. Run 1,000 creator-level nonparametric bootstrap resamples with seed `20260903`. Each draw resamples the full eligible population once and applies both fixed selection masks, preserving correlation from creators shared by the two lists.

Keeping top-N fixed is essential: otherwise a larger selected pool could create an apparent improvement without demonstrating a better allocation rule.

## 5. Offline results

| Metric | Existing rule | Adjusted rule | Change | 95% bootstrap interval |
|---|---:|---:|---:|---:|
| 30-day retention | 48.70% | 58.13% | +9.43 percentage points | [9.02, 9.88] pp |
| Revenue per unit of incentive | 69.59 | 78.43 | +12.71% | [11.00%, 14.51%] |
| Average cash incentive per creator | 550 | 625 | +13.6% | — |
| List overlap | — | — | 72.2% | — |

The adjusted list improves retention and revenue per unit of incentive, and both bootstrap intervals exclude zero. It also raises average cash support, so this is a trade-off rather than a free gain. The 72.2% overlap suggests a meaningful but bounded migration.

The reported +12.71% is calculated from the unrounded means (69.5853 and 78.4309). Dividing the one-decimal display values (69.6 and 78.4) produces +12.6% because those inputs have already lost precision; the two-decimal display above reconciles the arithmetic.

## 6. Interpretation boundary

These figures are synthetic offline back-test results. The bootstrap intervals quantify resampling uncertainty conditional on the fitted rules and observed synthetic creator population; they do not capture model-selection uncertainty. They also do not establish causal business impact, production safety, or a platform-wide benchmark. Safety and fraud fields are not present in the synthetic back-test and therefore are design requirements for an online experiment, not completed offline checks.

## 7. Implementation and quality checks

The Python implementation separates loading, validation, scoring, evaluation, and bootstrap inference. It rejects missing scoring fields, duplicate creator IDs, invalid eligibility flags, missing eligible outcomes, invalid bootstrap settings, non-positive pool sizes, and pool sizes larger than the eligible population before producing a result.

Nine regression tests verify the two published uplift figures and 95% intervals, top-N consistency, bootstrap settings, unique IDs, required columns, and valid pool size. GitHub Actions reruns the analysis and test suite on Python 3.11 and 3.12 after each repository change.

## 8. Proposed online validation

- Randomise at creator level within pre-defined strata.
- Use 30-day retention and revenue per unit of incentive as primary metrics.
- Monitor average incentive, creator churn, complaints, fraud, and content safety as guardrails.
- Check sample-ratio mismatch, assignment-to-exposure integrity, and treatment contamination.
- Pause expansion if efficiency turns negative or any critical risk guardrail deteriorates.

The offline evidence supports a controlled first test only. It does not support immediate full rollout.
