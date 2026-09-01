import math

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
