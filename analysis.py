from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DEFAULT_TOP_N = 4_200
DEFAULT_BOOTSTRAP_ITERATIONS = 1_000
DEFAULT_BOOTSTRAP_SEED = 20_260_903
REQUIRED_COLUMNS = {
    "creator_id",
    "join_date",
    "has_first_publish",
    "old_rule_score",
    "retention_30d_rate",
    "rev_per_1k_exposure",
    "total_supported_exposure",
    "exposure_pct_rank",
    "unit_incentive_revenue",
    "total_cash_incentive",
}


def validate_creator_data(creator: pd.DataFrame) -> None:
    """Fail early when the synthetic input cannot support the back-test."""
    missing = REQUIRED_COLUMNS - set(creator.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    if creator.empty:
        raise ValueError("Creator data are empty")
    if creator["creator_id"].isna().any():
        raise ValueError("creator_id contains missing values")
    if creator["creator_id"].duplicated().any():
        raise ValueError("creator_id must be unique")
    if not creator["has_first_publish"].isin([0, 1]).all():
        raise ValueError("has_first_publish must contain only 0 or 1")


def load_creator_data(path: Path | None = None) -> pd.DataFrame:
    """Load the synthetic creator-level table."""
    source = path or ROOT / "creator_profile.csv"
    creator = pd.read_csv(source, parse_dates=["join_date"])
    validate_creator_data(creator)
    return creator


def score_creators(creator: pd.DataFrame) -> pd.DataFrame:
    """Build the adjusted priority score for creators who published content."""
    validate_creator_data(creator)
    eligible = creator.loc[creator["has_first_publish"].eq(1)].copy()

    lower = eligible["rev_per_1k_exposure"].quantile(0.01)
    upper = eligible["rev_per_1k_exposure"].quantile(0.99)
    eligible["efficiency_winsorized"] = eligible[
        "rev_per_1k_exposure"
    ].clip(lower, upper)

    eligible["old_rule_pct_rank"] = eligible["old_rule_score"].rank(pct=True)
    eligible["retention_pct_rank"] = eligible["retention_30d_rate"].rank(pct=True)
    eligible["efficiency_pct_rank"] = eligible[
        "efficiency_winsorized"
    ].rank(pct=True)
    eligible["resource_pct_rank"] = eligible[
        "total_supported_exposure"
    ].rank(pct=True)

    eligible["segment"] = np.select(
        [
            (eligible["exposure_pct_rank"] >= 0.60)
            & (eligible["efficiency_pct_rank"] <= 0.52),
            (eligible["retention_pct_rank"] >= 0.65)
            & (eligible["efficiency_pct_rank"] >= 0.65)
            & (eligible["resource_pct_rank"] <= 0.68),
            (eligible["retention_pct_rank"] >= 0.72)
            & (eligible["efficiency_pct_rank"] >= 0.72),
            (eligible["exposure_pct_rank"] <= 0.25)
            & (eligible["efficiency_pct_rank"] <= 0.35),
        ],
        [
            "high-exposure / low-monetisation",
            "high-potential / low-incentive",
            "high-value stable supply",
            "low-value supply",
        ],
        default="general supply",
    )

    eligible["adjusted_priority_score"] = (
        0.60 * eligible["old_rule_pct_rank"]
        + 0.20 * eligible["retention_pct_rank"]
        + 0.15 * eligible["efficiency_pct_rank"]
        + 0.05 * (1 - eligible["resource_pct_rank"])
    )
    return eligible


def run_backtest(
    creator: pd.DataFrame, top_n: int = DEFAULT_TOP_N
) -> tuple[pd.DataFrame, float]:
    """Compare the existing and adjusted rules at the same selected-pool size."""
    if top_n <= 0:
        raise ValueError("top_n must be a positive integer")
    scored = score_creators(creator)
    if len(scored) < top_n:
        raise ValueError(
            f"top_n={top_n:,} exceeds the {len(scored):,} eligible creators"
        )

    existing = scored.nlargest(top_n, "old_rule_score")
    adjusted = scored.nlargest(top_n, "adjusted_priority_score")

    summary = pd.DataFrame(
        {
            "selection_rule": ["existing rule", "adjusted rule"],
            "selected_creators": [top_n, top_n],
            "retention_30d": [
                existing["retention_30d_rate"].mean(),
                adjusted["retention_30d_rate"].mean(),
            ],
            "revenue_per_incentive": [
                existing["unit_incentive_revenue"].mean(),
                adjusted["unit_incentive_revenue"].mean(),
            ],
            "cash_incentive_per_creator": [
                existing["total_cash_incentive"].mean(),
                adjusted["total_cash_incentive"].mean(),
            ],
        }
    )

    overlap = len(set(existing["creator_id"]) & set(adjusted["creator_id"])) / top_n
    return summary, overlap


def bootstrap_backtest(
    creator: pd.DataFrame,
    top_n: int = DEFAULT_TOP_N,
    iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
    confidence: float = 0.95,
    seed: int = DEFAULT_BOOTSTRAP_SEED,
) -> pd.DataFrame:
    """Estimate uncertainty around the two headline back-test lifts.

    The creator-level bootstrap resamples the full eligible population and applies
    the two fixed selection masks to every resample. Using the same draw for both
    rules preserves the correlation created by their overlapping creator lists.
    The intervals are conditional on the fitted ranking rules; they do not turn
    this synthetic offline comparison into a causal estimate.
    """
    if not isinstance(iterations, int) or isinstance(iterations, bool) or iterations <= 0:
        raise ValueError("iterations must be a positive integer")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("seed must be a non-negative integer")

    scored = score_creators(creator)
    if len(scored) < top_n:
        raise ValueError(
            f"top_n={top_n:,} exceeds the {len(scored):,} eligible creators"
        )
    if top_n <= 0:
        raise ValueError("top_n must be a positive integer")

    existing = scored.nlargest(top_n, "old_rule_score")
    adjusted = scored.nlargest(top_n, "adjusted_priority_score")
    existing_mask = scored["creator_id"].isin(existing["creator_id"]).to_numpy()
    adjusted_mask = scored["creator_id"].isin(adjusted["creator_id"]).to_numpy()
    retention = scored["retention_30d_rate"].to_numpy(dtype=float)
    efficiency = scored["unit_incentive_revenue"].to_numpy(dtype=float)

    if np.isnan(retention).any() or np.isnan(efficiency).any():
        raise ValueError("eligible outcome columns must not contain missing values")

    rng = np.random.default_rng(seed)
    retention_lifts = np.empty(iterations)
    efficiency_lifts = np.empty(iterations)

    for draw in range(iterations):
        sampled = rng.integers(0, len(scored), size=len(scored))
        sampled_existing = existing_mask[sampled]
        sampled_adjusted = adjusted_mask[sampled]

        existing_retention = retention[sampled][sampled_existing].mean()
        adjusted_retention = retention[sampled][sampled_adjusted].mean()
        existing_efficiency = efficiency[sampled][sampled_existing].mean()
        adjusted_efficiency = efficiency[sampled][sampled_adjusted].mean()

        retention_lifts[draw] = (
            adjusted_retention - existing_retention
        ) * 100
        efficiency_lifts[draw] = (
            adjusted_efficiency / existing_efficiency - 1
        ) * 100

    alpha = (1 - confidence) / 2
    lower_percentile = 100 * alpha
    upper_percentile = 100 * (1 - alpha)
    point_retention = (
        adjusted["retention_30d_rate"].mean()
        - existing["retention_30d_rate"].mean()
    ) * 100
    point_efficiency = (
        adjusted["unit_incentive_revenue"].mean()
        / existing["unit_incentive_revenue"].mean()
        - 1
    ) * 100

    return pd.DataFrame(
        {
            "metric": [
                "30-day retention lift",
                "Revenue per unit of incentive lift",
            ],
            "unit": ["percentage points", "percent"],
            "point_estimate": [point_retention, point_efficiency],
            "ci_low": [
                np.percentile(retention_lifts, lower_percentile),
                np.percentile(efficiency_lifts, lower_percentile),
            ],
            "ci_high": [
                np.percentile(retention_lifts, upper_percentile),
                np.percentile(efficiency_lifts, upper_percentile),
            ],
            "confidence_level": [confidence, confidence],
            "bootstrap_iterations": [iterations, iterations],
            "random_seed": [seed, seed],
        }
    )


def main() -> None:
    creator = load_creator_data()
    summary, overlap = run_backtest(creator)
    bootstrap = bootstrap_backtest(creator)

    existing = summary.iloc[0]
    adjusted = summary.iloc[1]
    retention_lift_pp = (
        adjusted["retention_30d"] - existing["retention_30d"]
    ) * 100
    efficiency_lift_pct = (
        adjusted["revenue_per_incentive"]
        / existing["revenue_per_incentive"]
        - 1
    ) * 100

    print(summary.to_string(index=False))
    print(f"30-day retention lift: {retention_lift_pp:.2f} percentage points")
    print(f"Revenue per unit of incentive lift: {efficiency_lift_pct:.2f}%")
    print(f"Top-{DEFAULT_TOP_N:,} list overlap: {overlap:.2%}")
    print("Creator-level paired bootstrap uncertainty:")
    for result in bootstrap.itertuples(index=False):
        print(
            f"  {result.metric}: {result.point_estimate:.2f} {result.unit} "
            f"(95% CI [{result.ci_low:.2f}, {result.ci_high:.2f}]; "
            f"{result.bootstrap_iterations:,} resamples; seed={result.random_seed})"
        )
    print(
        "Boundary: synthetic offline back-test; "
        "not evidence of live causal business impact."
    )


if __name__ == "__main__":
    main()
