WITH eligible_creators AS (
    SELECT
        creator_id,
        old_rule_score,
        total_cash_incentive,
        retention_30d_rate,
        unit_incentive_revenue,
        rev_per_1k_exposure,
        old_rule_pct,
        retention_pct,
        efficiency_pct,
        resource_pct,
        CASE
            WHEN retention_pct_rank >= 0.65 AND efficiency_pct_rank >= 0.65 AND resource_pct_rank <= 0.68 THEN 1
            ELSE 0
        END AS is_high_potential_under_incentivized,
        CASE
            WHEN safety_flag = 1 OR fraud_flag = 1 THEN 0
            WHEN active_weeks < 2 THEN 0
            ELSE 1
        END AS pass_entry_gate,
        (0.60 * old_rule_pct
         + 0.20 * retention_pct
         + 0.15 * efficiency_pct
         + 0.05 * (1 - resource_pct)) AS new_priority_score
    FROM creator_profile
    WHERE has_first_publish = 1
), gated_pool AS (
    SELECT *
    FROM eligible_creators
    WHERE pass_entry_gate = 1
), old_logic AS (
    SELECT *
    FROM gated_pool
    ORDER BY old_rule_score DESC
    LIMIT 4200
), new_rule AS (
    SELECT *
    FROM gated_pool
    ORDER BY new_priority_score DESC
    LIMIT 4200
)
SELECT
    'old_logic' AS scheme,
    COUNT(*) AS selected_creators,
    ROUND(AVG(retention_30d_rate), 4) AS retention_30d,
    ROUND(AVG(unit_incentive_revenue), 2) AS revenue_per_incentive,
    ROUND(AVG(total_cash_incentive), 2) AS cash_per_creator,
    ROUND(AVG(rev_per_1k_exposure), 2) AS revenue_per_1k_exposure,
    ROUND(AVG(is_high_potential_under_incentivized), 4) AS high_potential_hit_rate
FROM old_logic
UNION ALL
SELECT
    'new_rule' AS scheme,
    COUNT(*) AS selected_creators,
    ROUND(AVG(retention_30d_rate), 4) AS retention_30d,
    ROUND(AVG(unit_incentive_revenue), 2) AS revenue_per_incentive,
    ROUND(AVG(total_cash_incentive), 2) AS cash_per_creator,
    ROUND(AVG(rev_per_1k_exposure), 2) AS revenue_per_1k_exposure,
    ROUND(AVG(is_high_potential_under_incentivized), 4) AS high_potential_hit_rate
FROM new_rule;