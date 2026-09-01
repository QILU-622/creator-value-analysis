from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DEFAULT_TOP_N = 4_200


def load_creator_data(path: Path | None = None) -> pd.DataFrame:
    """Load the synthetic creator-level table."""
    source = path or ROOT / "creator_profile.csv"
    return pd.read_csv(source, parse_dates=["join_date"])


def score_creators(creator: pd.DataFrame) -> pd.DataFrame:
    """Build the adjusted priority score for creators who published content."""
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
