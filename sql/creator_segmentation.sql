WITH creator_scored AS (
    SELECT
        creator_id,
        retention_30d_rate,
        rev_per_1k_exposure,
        total_supported_exposure,
        total_cash_incentive,
        exposure_pct_rank,
        efficiency_pct_rank,
        retention_pct_rank,
        resource_pct_rank,
        CASE
            WHEN exposure_pct_rank >= 0.60 AND efficiency_pct_rank <= 0.52 THEN 'high-exposure / low-monetisation'
            WHEN retention_pct_rank >= 0.65 AND efficiency_pct_rank >= 0.65 AND resource_pct_rank <= 0.68 THEN 'high-potential / low-incentive'
            WHEN retention_pct_rank >= 0.72 AND efficiency_pct_rank >= 0.72 THEN 'high-value stable supply'
            WHEN exposure_pct_rank <= 0.25 AND efficiency_pct_rank <= 0.35 THEN 'low-value supply'
            ELSE 'general supply'
        END AS creator_segment
    FROM creator_profile
)
SELECT
    creator_segment,
    COUNT(*) AS creators,
    ROUND(COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (), 4) AS creator_share,
    ROUND(AVG(retention_30d_rate), 4) AS avg_retention_30d,
    ROUND(AVG(rev_per_1k_exposure), 2) AS avg_rev_per_1k_exposure,
    ROUND(SUM(total_supported_exposure) * 1.0 / SUM(SUM(total_supported_exposure)) OVER (), 4) AS exposure_share,
    ROUND(AVG(total_cash_incentive), 2) AS avg_cash_incentive
FROM creator_scored
GROUP BY 1
ORDER BY creators DESC;
