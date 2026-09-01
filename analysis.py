from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DEFAULT_TOP_N = 4_200
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


def main() -> None:
    creator = load_creator_data()
    summary, overlap = run_backtest(creator)

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
    print(
        "Boundary: synthetic offline back-test; "
        "not evidence of live causal business impact."
    )


if __name__ == "__main__":
    main()
