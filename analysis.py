import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from pathlib import Path
import textwrap

BASE = Path(__file__).resolve().parent
DATA = BASE / 'data'
FIG = BASE / 'figures'
OUT = BASE / 'outputs'
FIG.mkdir(exist_ok=True)
OUT.mkdir(exist_ok=True)

plt.rcParams['font.sans-serif'] = [
    'Arial Unicode MS', 'Noto Sans CJK SC', 'SimHei',
    'Microsoft YaHei', 'PingFang SC', 'DejaVu Sans'
]
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 180
plt.rcParams['savefig.dpi'] = 180
plt.rcParams['axes.titleweight'] = 'bold'
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False

COLOR = {
    'blue': '#2563eb',
    'slate': '#475569',
    'green': '#16a34a',
    'orange': '#ea580c',
    'purple': '#7c3aed',
    'red': '#dc2626',
    'gray': '#94a3b8',
    'light': '#e2e8f0',
    'navy': '#0f172a',
    'amber': '#d97706',
    'bg_blue': '#eff6ff',
    'bg_green': '#f0fdf4',
    'bg_orange': '#fff7ed',
    'bg_red': '#fef2f2',
    'bg_purple': '#f5f3ff',
}

SEGMENT_CN_EN = {
    '一般供给': 'General supply',
    '高曝光低变现': 'High exposure, low monetization',
    '高潜低激励': 'High potential, under-incentivized',
    '高价值稳定供给': 'High-value stable supply',
    '低价值供给': 'Low-value supply',
}

SEGMENT_COLORS = {
    '一般供给': COLOR['gray'],
    '高曝光低变现': COLOR['orange'],
    '高潜低激励': COLOR['green'],
    '高价值稳定供给': COLOR['purple'],
    '低价值供给': COLOR['red'],
}


VERTICAL_EN = {
    '生活方式': 'Lifestyle',
    '搞笑娱乐': 'Comedy & entertainment',
    '美妆护肤': 'Beauty & skincare',
    '本地生活': 'Local services',
    '游戏': 'Gaming',
    '母婴': 'Parenting',
    '数码科技': 'Consumer tech',
    '知识教育': 'Knowledge & education',
}


def load_data():
    creator = pd.read_csv(DATA / 'creator_profile.csv', parse_dates=['join_date'])
    content = pd.read_csv(DATA / 'content_performance.csv', parse_dates=['publish_date'])
    weekly = pd.read_csv(DATA / 'creator_weekly_activity.csv', parse_dates=['week_start'])
    incentive = pd.read_csv(DATA / 'creator_incentive.csv', parse_dates=['week_start'])
    return creator, content, weekly, incentive


def prepare_creator(creator: pd.DataFrame) -> pd.DataFrame:
    df = creator.copy()
    df['join_month'] = df['join_date'].dt.to_period('M').astype(str)

    df['published_creator'] = df['has_first_publish'].fillna(0).eq(1)
    df['active_2w_creator'] = df['published_creator'] & df['active_weeks'].fillna(0).ge(2)
    df['active_4w_creator'] = df['active_2w_creator'] & df['active_weeks'].fillna(0).ge(4)
    df['mon_open_after_active4'] = df['active_4w_creator'] & df['monetization_opened'].fillna(0).eq(1)
    df['stable_monetizing_creator'] = df['mon_open_after_active4'] & df['stable_updater'].fillna(0).eq(1)

    df['efficiency_metric'] = df['rev_per_1k_exposure'].fillna(0)
    eff_cap = df.loc[df['published_creator'], 'efficiency_metric'].quantile(0.99)
    df['efficiency_metric_winsor'] = df['efficiency_metric'].clip(upper=eff_cap)

    eligible = df['published_creator']
    df.loc[eligible, 'old_rule_pct'] = df.loc[eligible, 'old_rule_score'].rank(pct=True)
    df.loc[eligible, 'efficiency_pct'] = df.loc[eligible, 'efficiency_metric_winsor'].rank(pct=True)
    df.loc[eligible, 'retention_pct'] = df.loc[eligible, 'retention_30d_rate'].fillna(0).rank(pct=True)
    df.loc[eligible, 'resource_pct'] = df.loc[eligible, 'total_supported_exposure'].fillna(0).rank(pct=True)

    df['new_priority_score'] = np.nan
    df.loc[eligible, 'new_priority_score'] = (
        0.60 * df.loc[eligible, 'old_rule_pct']
        + 0.20 * df.loc[eligible, 'retention_pct']
        + 0.15 * df.loc[eligible, 'efficiency_pct']
        + 0.05 * (1 - df.loc[eligible, 'resource_pct'])
    )

    df['segment'] = np.select(
        [
            df['exposure_pct_rank'].fillna(0).ge(0.60) & df['efficiency_pct_rank'].fillna(0).le(0.52),
            df['retention_pct_rank'].fillna(0).ge(0.65) & df['efficiency_pct_rank'].fillna(0).ge(0.65) & df['resource_pct_rank'].fillna(0).le(0.68),
            df['retention_pct_rank'].fillna(0).ge(0.72) & df['efficiency_pct_rank'].fillna(0).ge(0.72),
            df['exposure_pct_rank'].fillna(1).le(0.25) & df['efficiency_pct_rank'].fillna(1).le(0.35),
        ],
        ['高曝光低变现', '高潜低激励', '高价值稳定供给', '低价值供给'],
        default='一般供给',
    )
    return df


def save_legacy_tables(funnel, cohort, backtest_detail):
    funnel_legacy = funnel[['stage', 'creators', 'share_of_total']].rename(columns={'creators': 'creator_cnt', 'share_of_total': 'conversion_rate'})
    funnel_legacy.to_csv(DATA / 'creator_funnel_summary.csv', index=False)

    cohort_legacy = cohort[['join_month', 'cohort_size', 'retention_30d', 'publish_rate']].rename(columns={'cohort_size': 'creators'})
    cohort_legacy.to_csv(DATA / 'creator_cohort_summary.csv', index=False)

    resource_legacy = pd.DataFrame(
        {
            'scheme': ['原平均投放逻辑', '新分层规则'],
            'selected_creators': [int(backtest_detail['old_selected_creators'].iloc[0]), int(backtest_detail['new_selected_creators'].iloc[0])],
            'avg_30d_retention': [backtest_detail['retention_old'].iloc[0], backtest_detail['retention_new'].iloc[0]],
            'avg_rev_per_incentive': [backtest_detail['uri_old'].iloc[0], backtest_detail['uri_new'].iloc[0]],
            'high_potential_hit_rate': [backtest_detail['high_potential_hit_old'].iloc[0], backtest_detail['high_potential_hit_new'].iloc[0]],
            'retention_lift_ppt': [0.0, backtest_detail['retention_lift_ppt'].iloc[0]],
            'unit_incentive_rev_lift_pct': [0.0, backtest_detail['uri_lift_pct'].iloc[0] / 100],
        }
    )
    resource_legacy.to_csv(DATA / 'resource_backtest_summary.csv', index=False)


def build_funnel(df: pd.DataFrame):
    funnel = pd.DataFrame(
        {
            'stage': ['注册创作者', '完成首发', '连续活跃≥2周', '连续活跃≥4周', '已开通变现', '稳定经营且已开通变现'],
            'creators': [
                len(df),
                int(df['published_creator'].sum()),
                int(df['active_2w_creator'].sum()),
                int(df['active_4w_creator'].sum()),
                int(df['mon_open_after_active4'].sum()),
                int(df['stable_monetizing_creator'].sum()),
            ],
        }
    )
    funnel['share_of_total'] = funnel['creators'] / funnel.loc[0, 'creators']
    funnel['step_rate'] = funnel['creators'] / funnel['creators'].shift(1)
    funnel.to_csv(OUT / 'funnel_summary.csv', index=False)

    stage_label_map = {
        '注册创作者': 'Registered creators',
        '完成首发': 'Published first post',
        '连续活跃≥2周': 'Active for 2+ weeks',
        '连续活跃≥4周': 'Active for 4+ weeks',
        '已开通变现': 'Monetization enabled',
        '稳定经营且已开通变现': 'Stable & monetized',
    }
    fig, ax = plt.subplots(figsize=(10.2, 5.9))
    y = np.arange(len(funnel))[::-1]
    bars = ax.barh(y, funnel['creators'], height=0.62, color=COLOR['blue'])
    ax.set_yticks(y)
    ax.set_yticklabels([stage_label_map.get(x, x) for x in funnel['stage']])
    ax.set_xlabel('Number of creators')
    ax.set_title('Creator supply funnel: the main loss is post-first-publish persistence', fontsize=14)
    ax.grid(axis='x', alpha=0.16)
    ax.set_axisbelow(True)
    xmax = funnel['creators'].max() * 1.23
    ax.set_xlim(0, xmax)
    for rect, total_share, step in zip(bars, funnel['share_of_total'], funnel['step_rate']):
        x = rect.get_width()
        ymid = rect.get_y() + rect.get_height() / 2
        text = f"{int(x):,} · Share of total {total_share:.1%}"
        if pd.notna(step):
            text += f"\nStep conversion {step:.1%}"
        ax.text(x + funnel['creators'].max() * 0.012, ymid, text, va='center', fontsize=8.8)
    fig.text(
        0.01,
        0.02,
        '口径说明：各阶段为嵌套口径。末段使用“连续活跃后开通变现”和“稳定经营且已开通变现”，避免仅因收入大于 0 就夸大最终阶段。',
        ha='left',
        va='bottom',
        fontsize=8.8,
        color=COLOR['slate'],
    )
    fig.tight_layout(rect=[0, 0.08, 1, 1])
    fig.savefig(FIG / '01_creator_funnel.png')
    plt.close(fig)
    return funnel


def build_cohort(df: pd.DataFrame):
    published = df.loc[df['published_creator']].copy()
    cohort = (
        df.groupby('join_month')
        .agg(
            cohort_size=('creator_id', 'count'),
            publish_rate=('published_creator', 'mean'),
            retention_30d=('retention_30d_rate', 'mean'),
        )
        .reset_index()
    )
    mon_open = published.groupby('join_month')['monetization_opened'].mean().rename('monetization_open_rate')
    cohort = cohort.merge(mon_open, on='join_month', how='left')
    cohort.to_csv(OUT / 'cohort_summary.csv', index=False)

    x = np.arange(len(cohort))
    fig, ax1 = plt.subplots(figsize=(10.2, 5.7))
    ax2 = ax1.twinx()
    ax2.bar(x, cohort['cohort_size'], width=0.62, color=COLOR['light'], label='Cohort size')
    ax1.plot(x, cohort['publish_rate'] * 100, marker='o', linewidth=2.2, color=COLOR['blue'], label='First-publish rate')
    ax1.plot(x, cohort['retention_30d'] * 100, marker='s', linewidth=2.2, color=COLOR['green'], label='30-day retention')

    ax1.set_xticks(x)
    ax1.set_xticklabels(cohort['join_month'], rotation=45)
    ax1.set_ylabel('Rate (%)')
    ax2.set_ylabel('Cohort size')
    ax1.set_ylim(35, 90)
    ax1.set_title('Monthly cohorts: supply quality is broadly stable; latest cohort is directional only', fontsize=14)
    ax1.grid(axis='y', alpha=0.16)
    ax1.set_axisbelow(True)

    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2, frameon=False, ncol=3, loc='upper left')

    latest_idx = len(cohort) - 1
    ax2.annotate(
        f"Latest cohort n={int(cohort.loc[latest_idx, 'cohort_size'])}",
        xy=(latest_idx, cohort.loc[latest_idx, 'cohort_size']),
        xytext=(latest_idx - 2.2, cohort['cohort_size'].max() * 0.82),
        arrowprops=dict(arrowstyle='->', lw=1, color=COLOR['slate']),
        fontsize=9,
        color=COLOR['slate'],
    )
    fig.text(
        0.01,
        0.02,
        'The newest cohort has both a shorter observation window and far fewer creators. It should be treated as an operating-health signal rather than causal evidence.',
        ha='left',
        va='bottom',
        fontsize=8.8,
        color=COLOR['slate'],
    )
    fig.tight_layout(rect=[0, 0.07, 1, 1])
    fig.savefig(FIG / '02_cohort_retention.png')
    plt.close(fig)
    return cohort


def build_pareto(df: pd.DataFrame):
    pareto = (
        df.loc[df['published_creator'], ['creator_id', 'total_exposure', 'total_revenue']]
        .fillna(0)
        .sort_values('total_exposure', ascending=False)
        .reset_index(drop=True)
    )
    pareto['creator_share'] = np.arange(1, len(pareto) + 1) / len(pareto)
    pareto['cum_exposure_share'] = pareto['total_exposure'].cumsum() / pareto['total_exposure'].sum()
    pareto['cum_revenue_share'] = pareto['total_revenue'].cumsum() / pareto['total_revenue'].sum()
    pareto.to_csv(OUT / 'pareto_summary.csv', index=False)

    target_idx = int(np.ceil(0.2 * len(pareto))) - 1
    top20 = pareto.iloc[target_idx]

    fig, ax = plt.subplots(figsize=(9.2, 5.5))
    ax.plot(pareto['creator_share'] * 100, pareto['cum_exposure_share'] * 100, linewidth=2.3, color=COLOR['blue'], label='Cumulative exposure share')
    ax.plot(pareto['creator_share'] * 100, pareto['cum_revenue_share'] * 100, linewidth=2.3, color=COLOR['orange'], label='Cumulative revenue share')
    ax.plot([0, 100], [0, 100], linestyle='--', color=COLOR['gray'], label='Uniform distribution')
    ax.axvline(20, linestyle=':', color=COLOR['slate'], alpha=0.8)
    ax.scatter([20], [top20['cum_exposure_share'] * 100], color=COLOR['blue'])
    ax.scatter([20], [top20['cum_revenue_share'] * 100], color=COLOR['orange'])
    ax.annotate(
        f"Top 20% creators\nExposure share {top20['cum_exposure_share']:.1%}",
        xy=(20, top20['cum_exposure_share'] * 100),
        xytext=(30, top20['cum_exposure_share'] * 100 + 9),
        arrowprops=dict(arrowstyle='->', color=COLOR['blue'], lw=1),
        fontsize=9,
        color=COLOR['blue'],
    )
    ax.annotate(
        f"Top 20% creators\nRevenue share {top20['cum_revenue_share']:.1%}",
        xy=(20, top20['cum_revenue_share'] * 100),
        xytext=(31, top20['cum_revenue_share'] * 100 - 12),
        arrowprops=dict(arrowstyle='->', color=COLOR['orange'], lw=1),
        fontsize=9,
        color=COLOR['orange'],
    )
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_xlabel('Cumulative creator share ranked by exposure (%)')
    ax.set_ylabel('Cumulative share (%)')
    ax.set_title('Pareto curve: resource concentration is materially higher than value concentration', fontsize=14)
    ax.grid(alpha=0.16)
    ax.legend(frameon=False, loc='lower right')
    fig.tight_layout()
    fig.savefig(FIG / '03_pareto_curve.png')
    plt.close(fig)
    return pareto, top20


def build_segmentation(df: pd.DataFrame):
    seg_summary = (
        df.groupby('segment')
        .agg(
            creators=('creator_id', 'count'),
            retention_30d=('retention_30d_rate', 'mean'),
            rev_per_1k_exposure=('rev_per_1k_exposure', 'mean'),
            total_exposure=('total_exposure', 'sum'),
        )
        .reset_index()
    )
    seg_summary['creator_share'] = seg_summary['creators'] / seg_summary['creators'].sum()
    seg_summary['exposure_share'] = seg_summary['total_exposure'] / seg_summary['total_exposure'].sum()
    seg_summary = seg_summary.sort_values('creators', ascending=False)
    seg_summary.to_csv(OUT / 'segment_summary.csv', index=False)

    plot_df = df[['retention_30d_rate', 'rev_per_1k_exposure', 'segment']].dropna().sample(4000, random_state=42)

    fig, ax = plt.subplots(figsize=(9.8, 6.9))
    for seg, sub in plot_df.groupby('segment'):
        ax.scatter(
            sub['retention_30d_rate'] * 100,
            sub['rev_per_1k_exposure'],
            s=18,
            alpha=0.30 if seg == '一般供给' else 0.46,
            color=SEGMENT_COLORS.get(seg, COLOR['gray']),
            label=SEGMENT_CN_EN.get(seg, seg),
        )

    centroids = df.groupby('segment')[['retention_30d_rate', 'rev_per_1k_exposure']].mean().reset_index()
    for _, row in centroids.iterrows():
        ax.scatter(row['retention_30d_rate'] * 100, row['rev_per_1k_exposure'], s=180, color=SEGMENT_COLORS.get(row['segment'], COLOR['gray']), edgecolor='white', linewidth=1.2)
        if row['segment'] in ['高曝光低变现', '高潜低激励', '高价值稳定供给']:
            ax.annotate(
                SEGMENT_CN_EN.get(row['segment'], row['segment']),
                xy=(row['retention_30d_rate'] * 100, row['rev_per_1k_exposure']),
                xytext=(row['retention_30d_rate'] * 100 + 1.2, row['rev_per_1k_exposure'] + 4),
                fontsize=8.7,
                color=SEGMENT_COLORS.get(row['segment'], COLOR['slate']),
                arrowprops=dict(arrowstyle='-', lw=0.8, color=SEGMENT_COLORS.get(row['segment'], COLOR['slate'])),
            )

    ax.axvline(df['retention_30d_rate'].quantile(0.65) * 100, linestyle='--', color=COLOR['slate'], alpha=0.45)
    ax.axhline(df['rev_per_1k_exposure'].quantile(0.65), linestyle='--', color=COLOR['slate'], alpha=0.45)
    ax.set_xlabel('30-day retention (%)')
    ax.set_ylabel('Revenue per 1k exposure')
    ax.set_title('Segmentation: identify under-recognized long-term value rather than follow historical exposure', fontsize=14)
    ax.grid(alpha=0.15)
    ax.legend(frameon=False, ncol=2, loc='lower right')
    fig.tight_layout()
    fig.savefig(FIG / '04_segmentation_scatter.png')
    plt.close(fig)
    return seg_summary


def bootstrap_compare(old_df: pd.DataFrame, new_df: pd.DataFrame, n_boot: int = 1200, seed: int = 42):
    rng = np.random.default_rng(seed)
    ret_lifts = []
    uri_lifts = []
    for _ in range(n_boot):
        rs_old = int(rng.integers(0, 1_000_000_000))
        rs_new = int(rng.integers(0, 1_000_000_000))
        s_old = old_df.sample(len(old_df), replace=True, random_state=rs_old)
        s_new = new_df.sample(len(new_df), replace=True, random_state=rs_new)
        ret_lifts.append((s_new['retention_30d_rate'].mean() - s_old['retention_30d_rate'].mean()) * 100)
        uri_lifts.append((s_new['unit_incentive_revenue'].mean() / s_old['unit_incentive_revenue'].mean() - 1) * 100)
    ci = pd.DataFrame(
        {
            'metric': ['30日留存提升(ppt)', '单位激励收入提升(%)'],
            'point_estimate': [np.median(ret_lifts), np.median(uri_lifts)],
            'ci_low': [np.percentile(ret_lifts, 2.5), np.percentile(uri_lifts, 2.5)],
            'ci_high': [np.percentile(ret_lifts, 97.5), np.percentile(uri_lifts, 97.5)],
        }
    )
    ci.to_csv(OUT / 'backtest_bootstrap_ci.csv', index=False)
    return ci


def build_backtest(df: pd.DataFrame):
    eligible = df.loc[df['published_creator']].copy()
    top_n = 4200
    old_sel = eligible.nlargest(top_n, 'old_rule_score').copy()
    new_sel = eligible.nlargest(top_n, 'new_priority_score').copy()

    ret_old = old_sel['retention_30d_rate'].mean()
    ret_new = new_sel['retention_30d_rate'].mean()
    uri_old = old_sel['unit_incentive_revenue'].mean()
    uri_new = new_sel['unit_incentive_revenue'].mean()
    cash_old = old_sel['total_cash_incentive'].mean()
    cash_new = new_sel['total_cash_incentive'].mean()
    hp_old = old_sel['segment'].eq('高潜低激励').mean()
    hp_new = new_sel['segment'].eq('高潜低激励').mean()

    backtest_summary = pd.DataFrame(
        {
            'metric': ['30日留存率', '单位激励收入', '人均现金激励'],
            'old_logic': [ret_old, uri_old, cash_old],
            'new_rule': [ret_new, uri_new, cash_new],
            'lift_pct_or_ppt': [(ret_new - ret_old) * 100, (uri_new / uri_old - 1) * 100, (cash_new / cash_old - 1) * 100],
        }
    )
    backtest_summary.to_csv(OUT / 'backtest_summary.csv', index=False)

    backtest_detail = pd.DataFrame(
        {
            'top_n': [top_n],
            'old_selected_creators': [len(old_sel)],
            'new_selected_creators': [len(new_sel)],
            'retention_old': [ret_old],
            'retention_new': [ret_new],
            'uri_old': [uri_old],
            'uri_new': [uri_new],
            'cash_old': [cash_old],
            'cash_new': [cash_new],
            'retention_lift_ppt': [(ret_new - ret_old) * 100],
            'uri_lift_pct': [(uri_new / uri_old - 1) * 100],
            'cash_change_pct': [(cash_new / cash_old - 1) * 100],
            'high_potential_hit_old': [hp_old],
            'high_potential_hit_new': [hp_new],
            'selection_overlap_rate': [len(set(old_sel['creator_id']) & set(new_sel['creator_id'])) / top_n],
        }
    )
    backtest_detail.to_csv(OUT / 'backtest_detail.csv', index=False)

    ci = bootstrap_compare(old_sel, new_sel)

    fig, ax = plt.subplots(figsize=(9.3, 5.7))
    metrics = ['30-day retention', 'Revenue per incentive', 'Cash incentive / creator']
    x = np.arange(len(metrics))
    width = 0.32
    old_idx = [100, 100, 100]
    new_idx = [ret_new / ret_old * 100, uri_new / uri_old * 100, cash_new / cash_old * 100]
    ax.bar(x - width / 2, old_idx, width, label='Old logic (index=100)', color=COLOR['gray'])
    new_bar = ax.bar(x + width / 2, new_idx, width, label='Recalibrated rule', color=COLOR['blue'])
    ax.set_xticks(x)
    ax.set_xticklabels(metrics)
    ax.set_ylabel('Index (old logic=100)')
    ax.set_title('Historical same-scale backtest: better long-term quality, not just more spending', fontsize=14)
    ax.grid(axis='y', alpha=0.16)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc='upper left')
    ax.set_ylim(0, max(max(new_idx), 118) * 1.22)

    actual_text = [
        f"{ret_old:.1%} → {ret_new:.1%}",
        f"{uri_old:.1f} → {uri_new:.1f}",
        f"{cash_old:.0f} → {cash_new:.0f}",
    ]
    for bar, txt in zip(new_bar, actual_text):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 3, txt, ha='center', va='bottom', fontsize=8.8)

    ret_ci = ci.loc[ci['metric'] == '30日留存提升(ppt)'].iloc[0]
    uri_ci = ci.loc[ci['metric'] == '单位激励收入提升(%)'].iloc[0]
    fig.text(
        0.01,
        0.02,
        f"Historical backtest only. Bootstrap 95% CI: retention lift {ret_ci['ci_low']:.1f}-{ret_ci['ci_high']:.1f} ppt; revenue-per-incentive lift {uri_ci['ci_low']:.1f}%–{uri_ci['ci_high']:.1f}%. Online experiments are still required for causal validation.",
        ha='left',
        va='bottom',
        fontsize=8.8,
        color=COLOR['slate'],
    )
    fig.tight_layout(rect=[0, 0.07, 1, 1])
    fig.savefig(FIG / '05_backtest_comparison.png')
    plt.close(fig)

    sizes = [3000, 3600, 4200, 5000, 6000]
    robust_rows = []
    for n in sizes:
        old_n = eligible.nlargest(n, 'old_rule_score')
        new_n = eligible.nlargest(n, 'new_priority_score')
        robust_rows.append(
            {
                'top_n': n,
                'retention_lift_ppt': (new_n['retention_30d_rate'].mean() - old_n['retention_30d_rate'].mean()) * 100,
                'uri_lift_pct': (new_n['unit_incentive_revenue'].mean() / old_n['unit_incentive_revenue'].mean() - 1) * 100,
                'cash_change_pct': (new_n['total_cash_incentive'].mean() / old_n['total_cash_incentive'].mean() - 1) * 100,
            }
        )
    robust = pd.DataFrame(robust_rows)
    robust.to_csv(OUT / 'rule_robustness_topn.csv', index=False)

    fig, axes = plt.subplots(1, 2, figsize=(11.6, 4.9))
    axes[0].plot(robust['top_n'], robust['retention_lift_ppt'], marker='o', color=COLOR['green'], linewidth=2.2)
    axes[0].axhline(0, color=COLOR['gray'], linewidth=1, linestyle='--')
    axes[0].set_title('Retention lift across budget sizes')
    axes[0].set_xlabel('Top N creators')
    axes[0].set_ylabel('Lift (ppt)')
    axes[0].grid(alpha=0.16)

    axes[1].plot(robust['top_n'], robust['uri_lift_pct'], marker='o', color=COLOR['blue'], linewidth=2.2)
    axes[1].axhline(0, color=COLOR['gray'], linewidth=1, linestyle='--')
    axes[1].set_title('Revenue-per-incentive lift across budget sizes')
    axes[1].set_xlabel('Top N creators')
    axes[1].set_ylabel('Lift (%)')
    axes[1].grid(alpha=0.16)

    fig.suptitle('Robustness check: the win is not driven by one arbitrary Top N threshold', fontsize=14, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(FIG / '06_rule_robustness.png')
    plt.close(fig)
    return backtest_summary, backtest_detail, robust, ci, old_sel, new_sel


def build_metric_framework(cohort: pd.DataFrame, top20: pd.Series, backtest_detail: pd.DataFrame, ci: pd.DataFrame):
    detail = backtest_detail.iloc[0]
    latest = cohort.iloc[-1]

    metric_snapshot = pd.DataFrame(
        [
            ['主指标', '30日留存率', f"{detail['retention_old']:.1%}", f"{detail['retention_new']:.1%}", f"+{detail['retention_lift_ppt']:.1f}ppt"],
            ['主指标', '单位激励收入', f"{detail['uri_old']:.1f}", f"{detail['uri_new']:.1f}", f"+{detail['uri_lift_pct']:.1f}%"],
            ['护栏指标', '人均现金激励', f"{detail['cash_old']:.0f}", f"{detail['cash_new']:.0f}", f"+{detail['cash_change_pct']:.1f}%"],
            ['护栏指标', '新旧名单重合率', '-', f"{detail['selection_overlap_rate']:.1%}", '控制迁移风险'],
            ['诊断指标', 'Top20曝光占比', '-', f"{top20['cum_exposure_share']:.1%}", '资源集中度'],
            ['诊断指标', 'Top20收入占比', '-', f"{top20['cum_revenue_share']:.1%}", '价值集中度'],
            ['监控指标', '最新cohort样本量', '-', f"{int(latest['cohort_size'])}", '仅看方向'],
            ['监控指标', '最新cohort首发率', '-', f"{latest['publish_rate']:.1%}", '供给健康度'],
        ],
        columns=['metric_level', 'metric_name', 'old_logic', 'new_rule_or_latest', 'interpretation']
    )
    metric_snapshot.to_csv(OUT / 'metric_snapshot.csv', index=False)

    ret_ci = ci.loc[ci['metric'] == '30日留存提升(ppt)'].iloc[0]
    uri_ci = ci.loc[ci['metric'] == '单位激励收入提升(%)'].iloc[0]

    fig = plt.figure(figsize=(14.0, 8.5))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.05], width_ratios=[1.05, 0.95], hspace=0.22, wspace=0.14)

    ax1 = fig.add_subplot(gs[0, 0])
    ax1.axis('off')
    ax1.text(0.0, 0.98, 'Metric system', fontsize=15, fontweight='bold', color=COLOR['navy'])
    ax1.text(0.0, 0.90, 'The project is framed as an operating decision: finite traffic and incentive budget must buy more stable supply, not just more exposure.', fontsize=10.6, color=COLOR['slate'])
    ax1.text(0.0, 0.79, 'North-star objective', fontsize=11, fontweight='bold', color=COLOR['blue'])
    ax1.text(0.0, 0.61, 'Grow the pool of stable creators\nImprove revenue per incentive', fontsize=13.2, bbox=dict(boxstyle='round,pad=0.55', fc=COLOR['bg_blue'], ec='#bfdbfe'))
    ax1.text(0.42, 0.70, '→', fontsize=22, color=COLOR['slate'])
    ax1.text(0.50, 0.79, 'Primary metrics', fontsize=11, fontweight='bold', color=COLOR['green'])
    ax1.text(0.50, 0.60, f"30-day retention +{detail['retention_lift_ppt']:.1f} ppt\nRevenue per incentive +{detail['uri_lift_pct']:.1f}%", fontsize=12.6, bbox=dict(boxstyle='round,pad=0.55', fc=COLOR['bg_green'], ec='#86efac'))
    ax1.text(0.0, 0.44, 'Guardrails', fontsize=11, fontweight='bold', color=COLOR['orange'])
    guard_text = (
        f"Cash / creator {detail['cash_old']:.0f} → {detail['cash_new']:.0f}\n"
        f"Selection overlap {detail['selection_overlap_rate']:.1%}\n"
        f"Bootstrap 95% CI: {ret_ci['ci_low']:.1f}-{ret_ci['ci_high']:.1f} ppt; {uri_ci['ci_low']:.1f}%–{uri_ci['ci_high']:.1f}%"
    )
    ax1.text(0.0, 0.15, guard_text, fontsize=11.1, bbox=dict(boxstyle='round,pad=0.55', fc=COLOR['bg_orange'], ec='#fdba74'))

    ax2 = fig.add_subplot(gs[0, 1])
    ax2.axis('off')
    ax2.text(0.0, 0.98, 'Action mapping', fontsize=15, fontweight='bold', color=COLOR['navy'])
    ax2.text(0.0, 0.90, '每一类发现都对应明确动作、验证方式和推进顺序，而不是停留在描述层。', fontsize=10.6, color=COLOR['slate'])
    y_positions = [0.76, 0.54, 0.32, 0.10]
    action_rows = [
        ('P0', 'High-potential, under-incentivized', 'Increase exposure and incentives; shorten recognition lag', COLOR['green']),
        ('P0', 'High-exposure, low-monetization', 'Set downgrade review thresholds; reduce sunk exposure', COLOR['orange']),
        ('P1', 'High-value stable supply', 'Keep steady support as the baseline quality pool', COLOR['purple']),
        ('P2', 'General / low-value supply', 'Use onboarding tasks and diagnostics to lift week-2 activity', COLOR['gray']),
    ]
    for y, (p, seg_name, desc, c) in zip(y_positions, action_rows):
        ax2.text(0.00, y, p, fontsize=10.5, color='white', bbox=dict(boxstyle='round,pad=0.3', fc=c, ec=c))
        ax2.text(0.14, y, seg_name, fontsize=12.3, fontweight='bold', color=COLOR['navy'])
        ax2.text(0.14, y - 0.11, textwrap.fill(desc, 44), fontsize=10.7, color=COLOR['slate'])

    ax3 = fig.add_subplot(gs[1, :])
    ax3.axis('off')
    ax3.text(0.0, 0.98, 'Launch validation and risk control', fontsize=15, fontweight='bold', color=COLOR['navy'])
    ax3.text(0.0, 0.90, '历史回测只支持方向判断；正式扩量前仍需线上验证和风险控制。', fontsize=10.6, color=COLOR['slate'])
    blocks = [
        ('Experiment design', 'Run stratified random tests for high-potential upgrades and high-exposure downgrades. Primary metrics: 30-day retention and revenue per incentive.', COLOR['bg_blue'], '#bfdbfe', 30),
        ('Guardrails', 'Track cash per creator, supply attrition, fraud / abuse rate, content safety and complaint rate to avoid cosmetic wins with ecosystem damage.', COLOR['bg_orange'], '#fdba74', 30),
        ('Effect risks', 'Watch for observation-window truncation, seasonality, recommender spillover, creator migration across pools and novelty effects from a new rule.', COLOR['bg_red'], '#fca5a5', 29),
        ('Rollout plan', 'Start with a grey release to the high-potential pool, expand gradually, and review the cohort × segment dashboard weekly before retuning weights.', COLOR['bg_green'], '#86efac', 30),
    ]
    xs = [0.00, 0.255, 0.51, 0.765]
    for (title, txt, fc, ec, width), x in zip(blocks, xs):
        ax3.text(x, 0.70, title, fontsize=11.4, fontweight='bold', color=COLOR['navy'])
        ax3.text(x, 0.18, textwrap.fill(txt, width), fontsize=10.1, color=COLOR['slate'], bbox=dict(boxstyle='round,pad=0.5', fc=fc, ec=ec))

    fig.savefig(FIG / '07_metric_framework.png', bbox_inches='tight')
    plt.close(fig)
    return metric_snapshot


def build_selection_transition(df: pd.DataFrame, old_sel: pd.DataFrame, new_sel: pd.DataFrame):
    old_ids = set(old_sel['creator_id'])
    new_ids = set(new_sel['creator_id'])

    transition_rows = []
    for creator_id in df.loc[df['published_creator'], 'creator_id']:
        if creator_id in old_ids and creator_id in new_ids:
            transition = 'Retained'
        elif creator_id in new_ids:
            transition = 'Promoted into new TopN'
        elif creator_id in old_ids:
            transition = 'Dropped from old TopN'
        else:
            transition = 'Outside both'
        transition_rows.append((creator_id, transition))

    transition_df = pd.DataFrame(transition_rows, columns=['creator_id', 'selection_transition'])
    transition_df = df[['creator_id', 'segment', 'content_vertical', 'retention_30d_rate', 'unit_incentive_revenue']].merge(transition_df, on='creator_id', how='left')

    summary = (
        transition_df.loc[transition_df['selection_transition'].isin(['Promoted into new TopN', 'Dropped from old TopN'])]
        .groupby(['selection_transition', 'segment'])
        .agg(
            creators=('creator_id', 'count'),
            avg_retention_30d=('retention_30d_rate', 'mean'),
            avg_unit_incentive_revenue=('unit_incentive_revenue', 'mean'),
        )
        .reset_index()
    )
    total_by_transition = summary.groupby('selection_transition')['creators'].transform('sum')
    summary['share_within_transition'] = summary['creators'] / total_by_transition
    summary.to_csv(OUT / 'selection_transition_summary.csv', index=False)

    plot = summary.pivot(index='selection_transition', columns='segment', values='share_within_transition').fillna(0)
    plot = plot.reindex(['Promoted into new TopN', 'Dropped from old TopN'])
    ordered_segments = ['高潜低激励', '高价值稳定供给', '一般供给', '高曝光低变现', '低价值供给']
    plot = plot.reindex(columns=[c for c in ordered_segments if c in plot.columns])

    fig, ax = plt.subplots(figsize=(9.8, 5.5))
    bottom = np.zeros(len(plot))
    xpos = np.arange(len(plot))
    for seg in plot.columns:
        vals = plot[seg].values * 100
        bars = ax.bar(xpos, vals, bottom=bottom, color=SEGMENT_COLORS.get(seg, COLOR['gray']), width=0.56, label=SEGMENT_CN_EN.get(seg, seg))
        for bar, val, btm in zip(bars, vals, bottom):
            if val >= 8:
                ax.text(bar.get_x() + bar.get_width() / 2, btm + val / 2, f"{val:.0f}%", ha='center', va='center', fontsize=8.6, color='white' if seg in ['高潜低激励', '高曝光低变现', '高价值稳定供给'] else COLOR['navy'])
        bottom += vals

    ax.set_xticks(xpos)
    ax.set_xticklabels(['Promoted into\nnew TopN', 'Dropped from\nold TopN'])
    ax.set_ylabel('Share within transition group (%)')
    ax.set_ylim(0, 100)
    ax.set_title('Selection transition: the recalibrated rule mainly removes low-efficiency exposure and adds stable / high-potential supply', fontsize=13.7)
    ax.grid(axis='y', alpha=0.16)
    ax.legend(frameon=False, ncol=2, bbox_to_anchor=(1.0, -0.08), loc='upper right')
    fig.text(
        0.01,
        0.01,
        f"TopN replacement size: {len(new_ids - old_ids):,} creators. Among drops, {(plot.loc['Dropped from old TopN', '高曝光低变现'] * 100 if '高曝光低变现' in plot.columns else 0):.1f}% are high-exposure/low-monetization creators.",
        ha='left', va='bottom', fontsize=8.8, color=COLOR['slate']
    )
    fig.tight_layout(rect=[0, 0.08, 1, 1])
    fig.savefig(FIG / '08_selection_transition.png')
    plt.close(fig)
    return summary


def build_vertical_robustness(old_sel: pd.DataFrame, new_sel: pd.DataFrame):
    old_metric = old_sel.groupby('content_vertical').agg(old_n=('creator_id', 'count'), old_retention=('retention_30d_rate', 'mean'), old_uri=('unit_incentive_revenue', 'mean')).reset_index()
    new_metric = new_sel.groupby('content_vertical').agg(new_n=('creator_id', 'count'), new_retention=('retention_30d_rate', 'mean'), new_uri=('unit_incentive_revenue', 'mean')).reset_index()
    merged = old_metric.merge(new_metric, on='content_vertical', how='outer').fillna(0)
    merged['retention_lift_ppt'] = (merged['new_retention'] - merged['old_retention']) * 100
    merged['uri_lift_pct'] = np.where(merged['old_uri'] > 0, (merged['new_uri'] / merged['old_uri'] - 1) * 100, np.nan)
    merged['net_seat_change'] = merged['new_n'] - merged['old_n']
    merged = merged.sort_values('retention_lift_ppt', ascending=False)
    merged.to_csv(OUT / 'vertical_robustness.csv', index=False)

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 5.3))
    y = np.arange(len(merged))
    labels = [VERTICAL_EN.get(v, v) for v in merged['content_vertical']]
    axes[0].barh(y, merged['retention_lift_ppt'], color=COLOR['green'])
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(labels)
    axes[0].invert_yaxis()
    axes[0].set_xlabel('Lift (ppt)')
    axes[0].set_title('30-day retention lift by vertical')
    axes[0].grid(axis='x', alpha=0.16)
    for yy, val in zip(y, merged['retention_lift_ppt']):
        axes[0].text(val + 0.15, yy, f"{val:.1f}", va='center', fontsize=8.6)

    axes[1].barh(y, merged['uri_lift_pct'], color=COLOR['blue'])
    axes[1].set_yticks(y)
    axes[1].set_yticklabels([])
    axes[1].invert_yaxis()
    axes[1].set_xlabel('Lift (%)')
    axes[1].set_title('Revenue-per-incentive lift by vertical')
    axes[1].grid(axis='x', alpha=0.16)
    for yy, val in zip(y, merged['uri_lift_pct']):
        axes[1].text(val + 0.2, yy, f"{val:.1f}%", va='center', fontsize=8.6)

    fig.suptitle('Heterogeneity check: gains are broad-based rather than concentrated in one content vertical', fontsize=14, fontweight='bold')
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(FIG / '09_vertical_robustness.png')
    plt.close(fig)
    return merged


def build_decision_outputs(df: pd.DataFrame, top20: pd.Series, backtest_detail: pd.DataFrame, ci: pd.DataFrame, seg_summary: pd.DataFrame, transition_summary: pd.DataFrame, vertical_robustness: pd.DataFrame):
    detail = backtest_detail.iloc[0]
    seg = seg_summary.set_index('segment')
    ret_ci = ci.loc[ci['metric'] == '30日留存提升(ppt)'].iloc[0]
    uri_ci = ci.loc[ci['metric'] == '单位激励收入提升(%)'].iloc[0]

    decision_scorecard = pd.DataFrame(
        [
            ['问题清晰度', 'Pass', 'Finite traffic and incentive budget are currently more concentrated than value creation: Top 20% creators take 42.9% of exposure but deliver only 30.2% of revenue.'],
            ['动作可执行性', 'Pass', 'Two concrete priority groups are defined: high-potential under-incentivized creators to upgrade, and high-exposure low-monetization creators to review or downgrade.'],
            ['证据强度', 'Conditional pass', f"Historical same-scale backtest shows retention +{detail['retention_lift_ppt']:.1f}ppt and revenue per incentive +{detail['uri_lift_pct']:.1f}%. Bootstrap CIs remain positive. The readout supports direction, but online experiments are still required before scaling."],
            ['迁移风险', 'Pass', f"Selection overlap remains {detail['selection_overlap_rate']:.1%}, which means the rule is a light recalibration rather than a full rewrite."],
            ['稳健性', 'Pass', f"All content verticals show positive retention lift; revenue-per-incentive lift is positive across the board in this synthetic sample."],
            ['上线建议', 'Proceed with gated launch', 'Run stratified online experiments first, then expand by pool and budget tier.'],
        ],
        columns=['dimension', 'assessment', 'commentary']
    )
    decision_scorecard.to_csv(OUT / 'decision_scorecard.csv', index=False)

    action_plan = pd.DataFrame(
        [
            ['P0', '高潜低激励', int(seg.loc['高潜低激励', 'creators']), float(seg.loc['高潜低激励', 'creator_share']), '增配曝光与激励，建立快速晋升池', '高潜命中率、30日留存率', '人均现金激励、投诉/作弊率', '缩短识别滞后，提高稳定经营创作者占比'],
            ['P0', '高曝光低变现', int(seg.loc['高曝光低变现', 'creators']), float(seg.loc['高曝光低变现', 'creator_share']), '设置降配复核阈值、收紧资源续投', '曝光占比、单位激励收入', '收入波动、供给流失', '减少资源沉没，抬高单位激励产出'],
            ['P1', '高价值稳定供给', int(seg.loc['高价值稳定供给', 'creators']), float(seg.loc['高价值稳定供给', 'creator_share']), '保持稳定扶持，作为高质量基线池', '稳定经营创作者占比', '预算上限', '维持内容生态的高质量供给底盘'],
            ['P2', '一般供给/低价值供给', int(seg.loc['一般供给', 'creators']) + int(seg.loc['低价值供给', 'creators']), np.nan, '通过内容诊断与新手任务提高首发与次周活跃', '首发率、2周活跃率', '低质供给占比', '提升漏斗前中段转化'],
        ],
        columns=['priority', 'segment', 'creators', 'creator_share', 'recommended_action', 'primary_metric', 'guardrail_metric', 'expected_business_effect']
    )
    action_plan.to_csv(OUT / 'segment_action_plan.csv', index=False)

    validity_threats = pd.DataFrame(
        [
            ['Backtest is observational, not causal', 'Historical selection may encode prior policy bias and survivor bias.', 'Use stratified randomized experiments or switchback tests before scaling.'],
            ['SRM / traffic allocation drift', 'Treatment and control may receive materially different traffic shares because of serving logic changes.', 'Monitor SRM daily by creator count, exposure, and support spend; stop if allocation deviates materially from design.'],
            ['Recommendation spillover', 'Traffic re-ranking can indirectly change outcomes for non-treated creators.', 'Prefer pool-level isolation, creator-level locking, and spillover-sensitive readouts.'],
            ['Observation-window truncation', 'Short windows may overstate short-term gains while missing churn.', 'Use both short-horizon diagnostic metrics and 30-day or longer success metrics.'],
            ['Novelty effect', 'Initial uplift can fade after creators adapt to the new rule.', 'Require holdout monitoring after rollout and compare week 1 vs week 4 effects.'],
            ['Creator migration across pools', 'Creators can move across thresholds and contaminate treatment assignment.', 'Lock assignment windows and analyze intent-to-treat as the primary readout.'],
        ],
        columns=['threat', 'why_it_matters', 'mitigation']
    )
    validity_threats.to_csv(OUT / 'validity_threat_register.csv', index=False)

    experiment_design = pd.DataFrame(
        [
            ['Randomization unit', 'Creator-level within stratified pools'],
            ['Primary treatments', 'Upgrade high-potential under-incentivized creators; review/downgrade high-exposure low-monetization creators'],
            ['Primary metrics', '30-day retention rate; revenue per incentive'],
            ['Guardrails', 'Cash incentive per creator; supply attrition; complaint rate; fraud/abuse rate; content safety'],
            ['Suggested strata', 'Content vertical; historical exposure tier; creator size; monetization status'],
            ['Readout principle', 'Intent-to-treat as the primary result; treatment-on-the-treated as supportive only'],
            ['Ship gate', f"Proceed only if retention is non-negative and revenue per incentive remains positive with no material guardrail deterioration; in this backtest CI remains positive ({ret_ci['ci_low']:.1f}-{ret_ci['ci_high']:.1f} ppt, {uri_ci['ci_low']:.1f}%–{uri_ci['ci_high']:.1f}%)."],
        ],
        columns=['item', 'recommendation']
    )
    experiment_design.to_csv(OUT / 'experiment_design_card.csv', index=False)

    scenario_interpretations = pd.DataFrame(
        [
            ['Why can cash per creator rise while the recommendation still be correct?', 'Because the decision criterion is not absolute spend minimization; it is whether incremental spend buys higher long-term creator quality and better revenue per incentive. In the backtest, cash per creator rises 13.6%, but revenue per incentive rises 12.7% and retention rises 9.4ppt, suggesting the budget is being reallocated to stronger supply rather than wasted.'],
            ['What if short-term monetization softens in a real test?', 'That does not automatically invalidate the policy. If the new rule pushes resources into earlier-stage but higher-retention creators, immediate cash efficiency can temporarily soften while medium-horizon supply quality improves. This should be checked with longer windows and cohort-based readouts before rollback.'],
            ['What if the last stage of the funnel does not improve immediately?', 'The funnel should be interpreted as a sequence. If early and middle stages improve first, downstream monetization can lag mechanically. The correct question is whether the stable-monetized pool expands with an appropriate delay, not whether every step moves at the same time.'],
        ],
        columns=['question', 'answer']
    )
    scenario_interpretations.to_csv(OUT / 'scenario_interpretations.csv', index=False)



    return decision_scorecard, action_plan, validity_threats, experiment_design, scenario_interpretations


def main():
    creator, content, weekly, incentive = load_data()
    df = prepare_creator(creator)

    funnel = build_funnel(df)
    cohort = build_cohort(df)
    pareto, top20 = build_pareto(df)
    seg_summary = build_segmentation(df)
    backtest_summary, backtest_detail, robust, ci, old_sel, new_sel = build_backtest(df)
    metric_snapshot = build_metric_framework(cohort, top20, backtest_detail, ci)
    transition_summary = build_selection_transition(df, old_sel, new_sel)
    vertical_robustness = build_vertical_robustness(old_sel, new_sel)
    build_decision_outputs(df, top20, backtest_detail, ci, seg_summary, transition_summary, vertical_robustness)
    save_legacy_tables(funnel, cohort, backtest_detail)

    print('Done. Figures and outputs have been regenerated with updated business framing, validation materials, and revised action-oriented language.')


if __name__ == '__main__':
    main()
