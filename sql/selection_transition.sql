WITH eligible_creators AS (
    SELECT
        creator_id,
        CASE
            WHEN exposure_pct_rank >= 0.60 AND efficiency_pct_rank <= 0.52 THEN 'high-exposure / low-monetisation'
            WHEN retention_pct_rank >= 0.65 AND efficiency_pct_rank >= 0.65 AND resource_pct_rank <= 0.68 THEN 'high-potential / low-incentive'
            WHEN retention_pct_rank >= 0.72 AND efficiency_pct_rank >= 0.72 THEN 'high-value stable supply'
            WHEN exposure_pct_rank <= 0.25 AND efficiency_pct_rank <= 0.35 THEN 'low-value supply'
            ELSE 'general supply'
        END AS creator_segment,
        old_rule_score,
        (0.60 * old_rule_pct
         + 0.20 * retention_pct
         + 0.15 * efficiency_pct
         + 0.05 * (1 - resource_pct)) AS new_priority_score
    FROM creator_profile
    WHERE has_first_publish = 1
), old_logic AS (
    SELECT creator_id
    FROM eligible_creators
    ORDER BY old_rule_score DESC
    LIMIT 4200
), new_rule AS (
    SELECT creator_id
    FROM eligible_creators
    ORDER BY new_priority_score DESC
    LIMIT 4200
), transitioned AS (
    SELECT
        e.creator_segment,
        CASE
            WHEN o.creator_id IS NOT NULL AND n.creator_id IS NOT NULL THEN 'retained'
            WHEN o.creator_id IS NULL AND n.creator_id IS NOT NULL THEN 'promoted_into_new_topn'
            WHEN o.creator_id IS NOT NULL AND n.creator_id IS NULL THEN 'dropped_from_old_topn'
            ELSE 'outside_both'
        END AS selection_transition
    FROM eligible_creators e
    LEFT JOIN old_logic o ON e.creator_id = o.creator_id
    LEFT JOIN new_rule n ON e.creator_id = n.creator_id
)
SELECT
    selection_transition,
    creator_segment,
    COUNT(*) AS creators,
    ROUND(COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (PARTITION BY selection_transition), 4) AS share_within_transition,
    CASE
        WHEN selection_transition = 'dropped_from_old_topn' AND creator_segment = 'high-exposure / low-monetisation' THEN 'the adjusted rule mainly removes low-efficiency exposure'
        WHEN selection_transition = 'promoted_into_new_topn' AND creator_segment IN ('high-potential / low-incentive','high-value stable supply') THEN 'the adjusted rule mainly adds higher-quality supply'
        ELSE 'use as transition-structure context'
    END AS interpretation
FROM transitioned
WHERE selection_transition IN ('promoted_into_new_topn', 'dropped_from_old_topn')
GROUP BY 1, 2
ORDER BY 1, creators DESC;
