WITH monthly_cohort AS (
    SELECT
        strftime(join_date, '%Y-%m') AS join_month,
        COUNT(*) AS creators,
        AVG(has_first_publish) AS publish_rate,
        AVG(retention_30d_rate) AS retention_30d_rate,
        AVG(CASE WHEN monetization_opened = 1 THEN 1 ELSE 0 END) AS monetization_open_rate,
        AVG(CASE WHEN active_weeks >= 4 THEN 1 ELSE 0 END) AS active_4w_rate
    FROM creator_profile
    GROUP BY 1
)
SELECT
    join_month,
    creators,
    ROUND(publish_rate, 4) AS publish_rate,
    ROUND(retention_30d_rate, 4) AS retention_30d_rate,
    ROUND(monetization_open_rate, 4) AS monetization_open_rate,
    ROUND(active_4w_rate, 4) AS active_4w_rate,
    CASE WHEN creators < 100 THEN '样本较小，仅作方向参考' ELSE '可用于稳定监控' END AS interpretation
FROM monthly_cohort
ORDER BY join_month;