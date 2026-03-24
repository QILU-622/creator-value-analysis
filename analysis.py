import pandas as pd
import numpy as np

TOP_N = 4200

creator = pd.read_csv('data/creator_profile.csv', parse_dates=['join_date'])
content = pd.read_csv('data/content_performance.csv', parse_dates=['publish_date'])
weekly = pd.read_csv('data/creator_weekly_activity.csv')
incentive = pd.read_csv('data/creator_incentive.csv')

# 1) 供给漏斗
funnel = pd.DataFrame({
    'stage': ['注册创作者','完成首发','连续活跃≥2周','连续活跃≥4周','已开通变现','稳定经营且已开通变现'],
    'creator_cnt': [
        len(creator),
        int(creator['has_first_publish'].sum()),
        int(((creator['has_first_publish'] == 1) & (creator['active_weeks'] >= 2)).sum()),
        int(((creator['has_first_publish'] == 1) & (creator['active_weeks'] >= 4)).sum()),
        int(((creator['has_first_publish'] == 1) & (creator['active_weeks'] >= 4) & (creator['monetization_opened'] == 1)).sum()),
        int(((creator['has_first_publish'] == 1) & (creator['active_weeks'] >= 4) & (creator['monetization_opened'] == 1) & (creator['stable_updater'] == 1)).sum())
    ]
})
funnel['share_of_registered'] = funnel['creator_cnt'] / funnel.loc[0, 'creator_cnt']
funnel['step_conversion'] = funnel['creator_cnt'] / funnel['creator_cnt'].shift(1)

# 2) 统一分位字段
eligible = creator[creator['has_first_publish'] == 1].copy()
low = eligible['rev_per_1k_exposure'].quantile(0.01)
high = eligible['rev_per_1k_exposure'].quantile(0.99)
eligible['efficiency_winsorized'] = eligible['rev_per_1k_exposure'].clip(low, high)

eligible['old_rule_pct_rank'] = eligible['old_rule_score'].rank(pct=True)
eligible['retention_pct_rank'] = eligible['retention_30d_rate'].rank(pct=True)
eligible['efficiency_pct_rank'] = eligible['efficiency_winsorized'].rank(pct=True)
eligible['resource_pct_rank'] = eligible['total_supported_exposure'].rank(pct=True)

# 3) 分层
eligible['segment'] = np.select([
    (eligible['exposure_pct_rank'] >= 0.60) & (eligible['efficiency_pct_rank'] <= 0.52),
    (eligible['retention_pct_rank'] >= 0.65) & (eligible['efficiency_pct_rank'] >= 0.65) & (eligible['resource_pct_rank'] <= 0.68),
    (eligible['retention_pct_rank'] >= 0.72) & (eligible['efficiency_pct_rank'] >= 0.72),
    (eligible['exposure_pct_rank'] <= 0.25) & (eligible['efficiency_pct_rank'] <= 0.35)
], ['高曝光低变现', '高潜低激励', '高价值稳定供给', '低价值供给'], default='一般供给')

# 4) 准入与排序
eligible['pass_entry_gate'] = np.where(
    (eligible['active_weeks'] >= 2)
    & (eligible['safety_flag'] == 0)
    & (eligible['fraud_flag'] == 0),
    1, 0
)
eligible['new_priority_score'] = (
    0.60 * eligible['old_rule_pct_rank']
    + 0.20 * eligible['retention_pct_rank']
    + 0.15 * eligible['efficiency_pct_rank']
    + 0.05 * (1 - eligible['resource_pct_rank'])
)

# 5) 固定 Top N 回测
pool = eligible[eligible['pass_entry_gate'] == 1].copy()
old_sel = pool.nlargest(TOP_N, 'old_rule_score')
new_sel = pool.nlargest(TOP_N, 'new_priority_score')

backtest = pd.DataFrame({
    '方案': ['原规则', '校正后规则'],
    '30日留存率': [old_sel['retention_30d_rate'].mean(), new_sel['retention_30d_rate'].mean()],
    '单位激励收入': [old_sel['unit_incentive_revenue'].mean(), new_sel['unit_incentive_revenue'].mean()],
    '人均现金激励': [old_sel['total_cash_incentive'].mean(), new_sel['total_cash_incentive'].mean()]
})

print(backtest)
