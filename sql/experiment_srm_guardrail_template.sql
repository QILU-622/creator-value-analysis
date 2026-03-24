-- 用于线上灰度期间的日级监控模板。
-- 目标：尽早发现 SRM、流量分配漂移、激励过量投放与关键护栏恶化。

WITH assignment_daily AS (
    SELECT
        event_date,
        experiment_group,
        creator_vertical,
        COUNT(DISTINCT creator_id) AS creators,
        SUM(exposure_cnt) AS exposure,
        SUM(cash_incentive) AS cash_incentive,
        SUM(revenue_amt) AS revenue_amt,
        SUM(retained_30d_flag) AS retained_creators,
        SUM(complaint_cnt) AS complaints,
        SUM(fraud_flag) AS fraud_cases,
        SUM(safety_case_cnt) AS safety_cases
    FROM creator_experiment_daily
    WHERE experiment_name = 'creator_resource_reallocation_v1'
    GROUP BY 1, 2, 3
), daily_totals AS (
    SELECT
        event_date,
        SUM(creators) AS total_creators,
        SUM(exposure) AS total_exposure
    FROM assignment_daily
    GROUP BY 1
), monitored AS (
    SELECT
        a.event_date,
        a.experiment_group,
        a.creator_vertical,
        a.creators,
        a.exposure,
        a.cash_incentive,
        a.revenue_amt,
        a.retained_creators,
        a.complaints,
        a.fraud_cases,
        a.safety_cases,
        a.creators * 1.0 / NULLIF(t.total_creators, 0) AS creator_share,
        a.exposure * 1.0 / NULLIF(t.total_exposure, 0) AS exposure_share
    FROM assignment_daily a
    JOIN daily_totals t
      ON a.event_date = t.event_date
)
SELECT
    event_date,
    experiment_group,
    creator_vertical,
    creators,
    ROUND(creator_share, 4) AS creator_share,
    ROUND(exposure_share, 4) AS exposure_share,
    ROUND(cash_incentive * 1.0 / NULLIF(creators, 0), 2) AS cash_per_creator,
    ROUND(revenue_amt * 1.0 / NULLIF(cash_incentive, 0), 2) AS revenue_per_incentive,
    ROUND(retained_creators * 1.0 / NULLIF(creators, 0), 4) AS retention_30d_proxy,
    ROUND(complaints * 1.0 / NULLIF(creators, 0), 4) AS complaints_per_creator,
    ROUND(fraud_cases * 1.0 / NULLIF(creators, 0), 4) AS fraud_rate,
    ROUND(safety_cases * 1.0 / NULLIF(creators, 0), 4) AS safety_rate,
    CASE
        WHEN ABS(creator_share - 0.5) > 0.03 THEN '检查 SRM / 分流漂移'
        WHEN revenue_amt * 1.0 / NULLIF(cash_incentive, 0) < 0 THEN '单位激励收入转负，暂停扩量'
        ELSE '继续监控'
    END AS action_hint
FROM monitored
ORDER BY event_date, creator_vertical, experiment_group;