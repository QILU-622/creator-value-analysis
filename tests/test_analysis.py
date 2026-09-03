import math

import pytest

from analysis import bootstrap_backtest, load_creator_data, run_backtest


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


def test_published_bootstrap_intervals_are_reproducible() -> None:
    bootstrap = bootstrap_backtest(load_creator_data())
    retention = bootstrap.iloc[0]
    efficiency = bootstrap.iloc[1]

    assert math.isclose(retention["point_estimate"], 9.4318333333, abs_tol=1e-8)
    assert math.isclose(retention["ci_low"], 9.0158963810, abs_tol=1e-8)
    assert math.isclose(retention["ci_high"], 9.8799215476, abs_tol=1e-8)
    assert math.isclose(efficiency["point_estimate"], 12.7118278980, abs_tol=1e-8)
    assert math.isclose(efficiency["ci_low"], 10.9986177345, abs_tol=1e-8)
    assert math.isclose(efficiency["ci_high"], 14.5119073929, abs_tol=1e-8)
    assert (bootstrap["ci_low"] > 0).all()


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"iterations": 0}, "iterations must be a positive integer"),
        ({"confidence": 1.0}, "confidence must be between 0 and 1"),
        ({"seed": -1}, "seed must be a non-negative integer"),
    ],
)
def test_bootstrap_configuration_fails_early(
    kwargs: dict[str, int | float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        bootstrap_backtest(load_creator_data(), **kwargs)
