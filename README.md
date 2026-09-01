# Creator Value Analysis and Resource Reallocation

A portfolio case study showing how Python and SQL can be used to diagnose resource misallocation, redesign a creator-prioritisation rule, evaluate it with a fixed-size offline back-test, and define a controlled online rollout.

> **Data disclosure:** All data in this repository are synthetic and were created solely for portfolio demonstration. They do not come from an employer, client, production platform, internship, or any confidential source.

## Decision question

When traffic and cash incentives are limited, are resources reaching creators who are more likely to deliver sustained supply and stronger output per unit of support?

The proposed decision rule combines four dimensions:

1. **Sustained supply:** 30-day retention, consecutive active weeks, and stable operating behaviour.
2. **Resource efficiency:** revenue per 1,000 impressions and revenue per unit of incentive.
3. **Supply quality:** monetisation activation and recent operating signals.
4. **Risk controls:** safety, fraud, complaints, migration cost, and operational capacity.

## Key offline back-test results

The comparison holds the selected group constant at the top 4,200 creators.

| Metric | Existing rule | Adjusted rule | Change |
|---|---:|---:|---:|
| 30-day retention | 48.7% | 58.1% | **+9.4 percentage points** |
| Revenue per unit of incentive | 69.6 | 78.4 | **+12.7%** |
| Average cash incentive per creator | 550 | 625 | +13.6% |
| List overlap | — | — | 72.2% |

These are **offline results on synthetic data**, not live business impact. They support testing the rule in a controlled experiment; they do not justify immediate full rollout.

## Analytical approach

- Diagnose the creator supply funnel and locate the main loss stage.
- Compare exposure concentration with value concentration.
- Segment creators into actionable groups, including high-exposure/low-monetisation and high-potential/low-incentive cohorts.
- Define safety, fraud, and activity eligibility gates for online implementation.
- Re-rank creators using retention, monetisation efficiency, and resource occupancy signals.
- Compare the existing and adjusted rules at a fixed top-N.
- Define primary metrics, guardrails, rollout thresholds, and rollback conditions for an online experiment.

## Run locally

```bash
git clone https://github.com/QILU-622/creator-value-analysis.git
cd creator-value-analysis

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

python -m pip install -r requirements.txt
python analysis.py
```

The analysis script reads the synthetic CSV inputs in the repository root and prints the fixed top-N back-test summary.

## Repository guide

- [`index.html`](index.html): portfolio overview and decision summary.
- [`report.html`](report.html): full business analysis and rollout logic.
- [`notebook.html`](notebook.html): analytical workflow and code excerpts.
- [`sql.html`](sql.html): SQL design for funnel analysis, segmentation, back-testing, and experiment monitoring.
- [`analysis.py`](analysis.py): Python implementation of the scoring and fixed top-N comparison.
- [`requirements.txt`](requirements.txt): Python dependencies.

## Decision boundary

The offline evidence supports a first controlled rollout only. Expansion should require positive primary metrics, stable guardrails, valid randomisation, and no material deterioration in complaints, fraud, safety, or creator churn.
