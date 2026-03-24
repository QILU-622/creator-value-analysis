WITH creator_base AS (
    SELECT
        creator_id,
        join_date,
        has_first_publish,
        active_weeks,
        monetization_opened,
        stable_updater,
        CASE WHEN has_first_publish = 1 THEN 1 ELSE 0 END AS published_creator,
        CASE WHEN has_first_publish = 1 AND active_weeks >= 2 THEN 1 ELSE 0 END AS active_2w_creator,
        CASE WHEN has_first_publish = 1 AND active_weeks >= 4 THEN 1 ELSE 0 END AS active_4w_creator,
        CASE WHEN has_first_publish = 1 AND active_weeks >= 4 AND monetization_opened = 1 THEN 1 ELSE 0 END AS monetization_after_active4,
        CASE WHEN has_first_publish = 1 AND active_weeks >= 4 AND monetization_opened = 1 AND stable_updater = 1 THEN 1 ELSE 0 END AS stable_monetizing_creator
    FROM creator_profile
), funnel_union AS (
    SELECT 1 AS step_order, '注册创作者' AS stage, COUNT(*) AS creator_cnt FROM creator_base
    UNION ALL
    SELECT 2, '完成首发', SUM(published_creator) FROM creator_base
    UNION ALL
    SELECT 3, '连续活跃≥2周', SUM(active_2w_creator) FROM creator_base
    UNION ALL
    SELECT 4, '连续活跃≥4周', SUM(active_4w_creator) FROM creator_base
    UNION ALL
    SELECT 5, '已开通变现', SUM(monetization_after_active4) FROM creator_base
    UNION ALL
    SELECT 6, '稳定经营且已开通变现', SUM(stable_monetizing_creator) FROM creator_base
)
SELECT
    stage,
    creator_cnt,
    ROUND(creator_cnt * 1.0 / FIRST_VALUE(creator_cnt) OVER (ORDER BY step_order), 4) AS share_of_registered,
    ROUND(creator_cnt * 1.0 / LAG(creator_cnt) OVER (ORDER BY step_order), 4) AS step_conversion
FROM funnel_union
ORDER BY step_order;