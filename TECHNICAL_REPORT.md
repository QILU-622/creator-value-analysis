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

Keeping top-N fixed is essential: otherwise a larger selected pool could create an apparent improvement without demonstrating a better allocation rule.

## 5. Offline results

| Metric | Existing rule | Adjusted rule | Change |
|---|---:|---:|---:|
| 30-day retention | 48.7% | 58.1% | +9.4 percentage points |
| Revenue per unit of incentive | 69.6 | 78.4 | +12.7% |
| Average cash incentive per creator | 550 | 625 | +13.6% |
| List overlap | — | — | 72.2% |

The adjusted list improves retention and revenue per unit of incentive, but it also raises average cash support. This is a trade-off, not a free gain. The 72.2% overlap suggests a meaningful but bounded migration.

## 6. Interpretation boundary

These figures are synthetic offline back-test results. They do not establish causal business impact, production safety, or a platform-wide benchmark. Safety and fraud fields are not present in the synthetic back-test and therefore are design requirements for an online experiment, not completed offline checks.

## 7. Proposed online validation

- Randomise at creator level within pre-defined strata.
- Use 30-day retention and revenue per unit of incentive as primary metrics.
- Monitor average incentive, creator churn, complaints, fraud, and content safety as guardrails.
- Check sample-ratio mismatch, assignment-to-exposure integrity, and treatment contamination.
- Pause expansion if efficiency turns negative or any critical risk guardrail deteriorates.

The offline evidence supports a controlled first test only. It does not support immediate full rollout.
