WITH eligible_creators AS (
    SELECT
        creator_id,
        CASE
            WHEN exposure_pct_rank >= 0.60 AND efficiency_pct_rank <= 0.52 THEN '高曝光低变现'
            WHEN retention_pct_rank >= 0.65 AND efficiency_pct_rank >= 0.65 AND resource_pct_rank <= 0.68 THEN '高潜低激励'
            WHEN retention_pct_rank >= 0.72 AND efficiency_pct_rank >= 0.72 THEN '高价值稳定供给'
            WHEN exposure_pct_rank <= 0.25 AND efficiency_pct_rank <= 0.35 THEN '低价值供给'
            ELSE '一般供给'
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
        WHEN selection_transition = 'dropped_from_old_topn' AND creator_segment = '高曝光低变现' THEN '主要说明新规则在回收低效率曝光'
        WHEN selection_transition = 'promoted_into_new_topn' AND creator_segment IN ('高潜低激励','高价值稳定供给') THEN '主要说明新规则在补进更高质量供给'
        ELSE '作为迁移结构参考'
    END AS interpretation
FROM transitioned
WHERE selection_transition IN ('promoted_into_new_topn', 'dropped_from_old_topn')
GROUP BY 1, 2
ORDER BY 1, creators DESC;