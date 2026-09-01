import math

import pytest

from analysis import load_creator_data, run_backtest


def test_published_backtest_metrics() -> None:
    summary, overlap = run_backtest(load_creator_data())
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

    assert math.isclose(retention_lift_pp, 9.4318333333, abs_tol=1e-8)
    assert math.isclose(efficiency_lift_pct, 12.7118278980, abs_tol=1e-8)
    assert math.isclose(overlap, 0.7219047619, abs_tol=1e-10)


def test_both_rules_hold_pool_size_constant() -> None:
    summary, _ = run_backtest(load_creator_data(), top_n=4_200)
    assert summary["selected_creators"].tolist() == [4_200, 4_200]


def test_backtest_rejects_non_positive_pool_size() -> None:
    with pytest.raises(ValueError, match="positive integer"):
        run_backtest(load_creator_data(), top_n=0)


def test_input_requires_unique_creator_ids() -> None:
    creator = load_creator_data().head(2).copy()
    creator.loc[1, "creator_id"] = creator.loc[0, "creator_id"]

    with pytest.raises(ValueError, match="must be unique"):
        run_backtest(creator, top_n=1)


def test_input_requires_the_scoring_columns() -> None:
    creator = load_creator_data().drop(columns=["old_rule_score"])

    with pytest.raises(ValueError, match="old_rule_score"):
        run_backtest(creator, top_n=1)
