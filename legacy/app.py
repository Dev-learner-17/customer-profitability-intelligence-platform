import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

# ═══════════════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="APL Logistics | Command Center",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════════════
#  GLOBAL STYLES
# ═══════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background: #0A0F1E;
    color: #E2E8F0;
}
[data-testid="stAppViewContainer"] { background: #0A0F1E; }
[data-testid="stSidebar"]          { background: #0D1426; border-right: 1px solid #1E2D4A; }
[data-testid="stHeader"]           { background: transparent; }
section[data-testid="stSidebar"] > div { padding-top: 1rem; }

/* ── KPI Cards ── */
.kpi-card {
    background: linear-gradient(135deg, #0F1E3A 0%, #162444 100%);
    border: 1px solid #1E3A5F;
    border-top: 3px solid #3B82F6;
    border-radius: 12px;
    padding: 16px 18px 14px 18px;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    min-height: 112px;
    box-sizing: border-box;
}
.kpi-card:hover { transform: translateY(-2px); box-shadow: 0 8px 32px rgba(59,130,246,0.2); }
.kpi-card::before {
    content: '';
    position: absolute; top: 0; right: 0;
    width: 64px; height: 64px;
    background: radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%);
    border-radius: 50%;
}
.kpi-label {
    font-size: 0.63rem; font-weight: 700;
    letter-spacing: 0.15em; text-transform: uppercase;
    color: #64748B; margin-bottom: 8px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
/* Value row: number + unit on same baseline, never wraps */
.kpi-value-row {
    display: flex;
    align-items: baseline;
    gap: 3px;
    line-height: 1;
    margin-bottom: 6px;
    flex-wrap: nowrap;
}
.kpi-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.65rem; font-weight: 700;
    color: #F1F5F9; line-height: 1;
    white-space: nowrap;
}
.kpi-unit {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.95rem; font-weight: 600;
    color: #94A3B8; line-height: 1;
    white-space: nowrap;
    align-self: flex-end; padding-bottom: 2px;
}
/* Legacy .kpi-value fallback for non-split cards */
.kpi-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.65rem; font-weight: 700;
    color: #F1F5F9; line-height: 1;
    white-space: nowrap;
}
.kpi-sub {
    font-size: 0.68rem; color: #64748B; margin-top: 2px;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.kpi-delta-pos { color: #10B981; font-size: 0.72rem; font-weight: 600; margin-top: 4px; display:block; }
.kpi-delta-neg { color: #EF4444; font-size: 0.72rem; font-weight: 600; margin-top: 4px; display:block; }
/* Filter-active badge on card */
.kpi-filtered { border-top-color: #F59E0B !important; }
.kpi-filter-badge {
    position: absolute; top: 8px; right: 10px;
    font-size: 0.55rem; font-weight: 700; letter-spacing: 0.1em;
    color: #F59E0B; text-transform: uppercase;
    background: rgba(245,158,11,0.12); border: 1px solid rgba(245,158,11,0.3);
    border-radius: 4px; padding: 1px 5px;
}

/* KPI accent colours */
.kpi-blue  { border-top-color: #3B82F6; }
.kpi-green { border-top-color: #10B981; }
.kpi-amber { border-top-color: #F59E0B; }
.kpi-red   { border-top-color: #EF4444; }
.kpi-violet{ border-top-color: #8B5CF6; }
.kpi-cyan  { border-top-color: #06B6D4; }

/* ── Section Headers ── */
.section-title {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.18em;
    text-transform: uppercase; color: #3B82F6;
    border-bottom: 1px solid #1E2D4A; padding-bottom: 8px;
    margin: 28px 0 18px 0;
}
.tab-hero {
    background: linear-gradient(135deg, #0F1E3A 0%, #101828 100%);
    border: 1px solid #1E2D4A; border-radius: 12px;
    padding: 20px 28px; margin-bottom: 24px;
}
.tab-hero h2 { margin: 0 0 4px 0; font-size: 1.25rem; font-weight: 700; color: #F1F5F9; }
.tab-hero p  { margin: 0; font-size: 0.82rem; color: #64748B; }

/* ── Insight Pills ── */
.insight-pill {
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    font-size: 0.72rem; font-weight: 600; margin: 2px;
}
.pill-danger  { background: rgba(239,68,68,0.15);  color: #F87171; border: 1px solid rgba(239,68,68,0.3); }
.pill-warning { background: rgba(245,158,11,0.15); color: #FCD34D; border: 1px solid rgba(245,158,11,0.3); }
.pill-success { background: rgba(16,185,129,0.15); color: #34D399; border: 1px solid rgba(16,185,129,0.3); }
.pill-info    { background: rgba(59,130,246,0.15);  color: #60A5FA; border: 1px solid rgba(59,130,246,0.3); }

/* ── Alert Boxes ── */
.alert-critical {
    background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.3);
    border-left: 4px solid #EF4444; border-radius: 8px;
    padding: 12px 16px; margin: 8px 0; font-size: 0.82rem;
}
.alert-warning {
    background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.3);
    border-left: 4px solid #F59E0B; border-radius: 8px;
    padding: 12px 16px; margin: 8px 0; font-size: 0.82rem;
}
.alert-success {
    background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.3);
    border-left: 4px solid #10B981; border-radius: 8px;
    padding: 12px 16px; margin: 8px 0; font-size: 0.82rem;
}
.alert-info {
    background: rgba(59,130,246,0.08); border: 1px solid rgba(59,130,246,0.3);
    border-left: 4px solid #3B82F6; border-radius: 8px;
    padding: 12px 16px; margin: 8px 0; font-size: 0.82rem;
}

/* ── Sidebar Controls ── */
.sidebar-section {
    background: #111827; border: 1px solid #1E2D4A; border-radius: 8px;
    padding: 14px; margin-bottom: 12px;
}
.sidebar-label {
    font-size: 0.65rem; letter-spacing: 0.12em; text-transform: uppercase;
    color: #3B82F6; font-weight: 700; margin-bottom: 8px;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: #0D1426; border-bottom: 1px solid #1E2D4A; gap: 0;
}
.stTabs [data-baseweb="tab"] {
    background: transparent; color: #64748B;
    font-size: 0.78rem; font-weight: 600;
    padding: 12px 20px; border-radius: 0;
    border-bottom: 3px solid transparent;
    transition: all 0.2s;
}
.stTabs [aria-selected="true"] {
    color: #3B82F6 !important;
    border-bottom-color: #3B82F6 !important;
    background: rgba(59,130,246,0.06) !important;
}

/* ── Plotly chart bg fix ── */
.js-plotly-plot { border-radius: 10px; }

/* ── Dataframe ── */
[data-testid="stDataFrame"] { border-radius: 8px; overflow: hidden; }

/* ── Metric overrides ── */
div[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 1.4rem !important; color: #F1F5F9 !important;
}
div[data-testid="stMetricLabel"] { color: #64748B !important; font-size: 0.75rem !important; }

/* ── Logo / brand area ── */
.brand-header {
    padding: 16px 0 12px 0; text-align: center;
    border-bottom: 1px solid #1E2D4A; margin-bottom: 16px;
}
.brand-name { font-size: 1.1rem; font-weight: 700; color: #F1F5F9; letter-spacing: 0.02em; }
.brand-sub  { font-size: 0.68rem; color: #3B82F6; letter-spacing: 0.12em; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════
#  PLOTLY THEME
# ═══════════════════════════════════════════════════════════════════════
DARK_TEMPLATE = go.layout.Template()
DARK_TEMPLATE.layout = go.Layout(
    paper_bgcolor="#0D1426",
    plot_bgcolor="#0D1426",
    font={"family": "Inter", "color": "#CBD5E1", "size": 12},
    title={"font": {"size": 14, "color": "#F1F5F9", "family": "Inter"}, "x": 0.01},
    xaxis={"gridcolor": "#1E2D4A", "linecolor": "#1E2D4A", "zerolinecolor": "#1E2D4A", "tickfont": {"size": 11}},
    yaxis={"gridcolor": "#1E2D4A", "linecolor": "#1E2D4A", "zerolinecolor": "#1E2D4A", "tickfont": {"size": 11}},
    legend={"bgcolor": "rgba(13,20,38,0.8)", "bordercolor": "#1E2D4A", "borderwidth": 1, "font": {"size": 11}},
    hoverlabel={"bgcolor": "#162444", "bordercolor": "#3B82F6", "font": {"family": "Inter", "size": 12}},
    colorway=["#3B82F6","#10B981","#F59E0B","#EF4444","#8B5CF6","#06B6D4","#F97316","#EC4899"],
    margin={"t": 44, "l": 12, "r": 12, "b": 12},
)

PALETTE = {
    "blue":   "#3B82F6",
    "green":  "#10B981",
    "amber":  "#F59E0B",
    "red":    "#EF4444",
    "violet": "#8B5CF6",
    "cyan":   "#06B6D4",
    "orange": "#F97316",
    "pink":   "#EC4899",
}

def apply_dark(fig, height=400):
    fig.update_layout(template=DARK_TEMPLATE, height=height)
    return fig


# ═══════════════════════════════════════════════════════════════════════
#  DATA LOADING
# ═══════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner="🔄 Loading intelligence layer…")
def load_all():
    base = Path("processed_data")
    agg  = base / "aggregations"
    ml   = base / "ml"

    def pq(p):
        try:
            return pd.read_parquet(p)
        except Exception:
            return pd.DataFrame()

    with open(base / "macro_kpis.json") as f:
        kpis = json.load(f)

    insights = {}
    ins_path = base / "analytics" / "analytics_insights.json"
    if ins_path.exists():
        with open(ins_path) as f:
            insights = json.load(f)

    ml_report = {}
    ml_path = ml / "model_report.json"
    if ml_path.exists():
        with open(ml_path) as f:
            ml_report = json.load(f)

    return {
        "kpis": kpis,
        "insights": insights,
        "ml_report": ml_report,
        "df_cust": pq(agg / "customer_agg.parquet"),
        "df_seg": pq(agg / "segmented_customers.parquet"),
        "df_rfm": pq(agg / "rfm_segments.parquet"),
        "df_cat": pq(agg / "category_agg.parquet"),
        "df_cat_h": pq(agg / "category_health.parquet"),
        "df_market": pq(agg / "market_agg.parquet"),
        "df_region": pq(agg / "region_agg.parquet"),
        "df_product": pq(agg / "product_agg.parquet"),
        "df_abc": pq(agg / "abc_classification.parquet"),
        "df_ship": pq(agg / "shipping_agg.parquet"),
        "df_base": pq(base / "ui_sample.parquet"),
        "df_trend": pq(base / "monthly_trend.parquet"),
        "df_margin": pq(ml   / "margin_risk_scored_orders.parquet"),
        "df_ltv": pq(ml   / "customer_ltv_scored.parquet"),
    }

D = load_all()
kpis, insights, ml_report = D["kpis"], D["insights"], D["ml_report"]


# ═══════════════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div class="brand-header">
        <div class="brand-name">🚢 APL Logistics</div>
        <div class="brand-sub">Intelligence Command Center</div>
    </div>
    """, unsafe_allow_html=True)

    def uniq(df, col):
        return sorted(df[col].dropna().unique().tolist()) if (not df.empty and col in df.columns) else []

    seg_opts = uniq(D["df_base"], "Customer Segment")
    cat_opts = uniq(D["df_base"], "Category Name")
    mkt_opts = uniq(D["df_base"], "Market")

    st.markdown('<div class="sidebar-section"><div class="sidebar-label">🔍 Filters</div>', unsafe_allow_html=True)
    sel_segs = st.multiselect("Customer Segment", seg_opts, placeholder="All segments")
    sel_cats = st.multiselect("Category", cat_opts, placeholder="All categories")
    sel_mkts = st.multiselect("Market", mkt_opts, placeholder="All markets")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section"><div class="sidebar-label">💰 Pricing Simulator</div>', unsafe_allow_html=True)
    disc_cap = st.slider("Max Discount Cap", 0.0, 0.50, 0.25, 0.01, format="%.0f%%",
                         help="Simulated policy cap on discount rates")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-section"><div class="sidebar-label">🤖 ML Controls</div>', unsafe_allow_html=True)
    risk_thresh = st.slider("Margin Risk Threshold", 0.30, 0.90, 0.50, 0.05, format="%.2f",
                            help="Orders above this score flagged as high-risk")
    top_n_cust = st.slider("Top N Customers", 5, 50, 15, 5)
    st.markdown('</div>', unsafe_allow_html=True)

    # Live stats
    st.markdown('<div class="sidebar-section"><div class="sidebar-label">📡 Live Stats</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="font-size:0.78rem; color:#94A3B8; line-height:1.8;">
    Orders: <b style="color:#F1F5F9">{kpis.get('n_orders',0):,}</b><br>
    Customers: <b style="color:#F1F5F9">{kpis.get('n_unique_customers',0):,}</b><br>
    Revenue: <b style="color:#F1F5F9">${kpis.get('total_revenue_usd',0)/1e6:.2f}M</b><br>
    Margin: <b style="color:#10B981">{kpis.get('profit_margin_pct',0):.2f}%</b>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Apply filters ──
filtered = D["df_base"].copy()
if sel_segs and "Customer Segment" in filtered.columns:
    filtered = filtered[filtered["Customer Segment"].isin(sel_segs)]
if sel_cats and "Category Name" in filtered.columns:
    filtered = filtered[filtered["Category Name"].isin(sel_cats)]
if sel_mkts and "Market" in filtered.columns:
    filtered = filtered[filtered["Market"].isin(sel_mkts)]

filter_active = bool(sel_segs or sel_cats or sel_mkts)
n_filtered = len(filtered)


# ═══════════════════════════════════════════════════════════════════════
#  HELPER: KPI CARD HTML  (fully inline-styled — no external CSS needed)
# ═══════════════════════════════════════════════════════════════════════
_ACCENT = {
    "blue":   "#3B82F6",
    "green":  "#10B981",
    "amber":  "#F59E0B",
    "red":    "#EF4444",
    "violet": "#8B5CF6",
    "cyan":   "#06B6D4",
}

def kpi_card(label, value, sub=None, delta=None, delta_pos=True, color="blue", icon="", is_filtered=False):
    """
    value: plain string  OR  (number_str, unit_str) tuple.
    Tuple keeps number and unit on the same baseline — no wrapping.
    All styles are inlined so Streamlit column shadow-DOM never breaks them.
    """
    accent       = _ACCENT.get(color, "#3B82F6")
    border_top   = "#F59E0B" if is_filtered else accent
    card_style   = (
        f"background:linear-gradient(135deg,#0F1E3A 0%,#162444 100%);"
        f"border:1px solid #1E3A5F;"
        f"border-top:3px solid {border_top};"
        f"border-radius:12px;"
        f"padding:16px 18px 14px 18px;"
        f"position:relative;"
        f"min-height:108px;"
        f"box-sizing:border-box;"
        f"font-family:'Inter',sans-serif;"
    )
    label_style  = (
        "font-size:0.63rem;font-weight:700;letter-spacing:0.14em;"
        "text-transform:uppercase;color:#64748B;margin-bottom:8px;"
        "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
        "display:block;"
    )
    num_style    = (
        "font-family:'JetBrains Mono',monospace;"
        "font-size:1.65rem;font-weight:700;color:#F1F5F9;"
        "line-height:1;white-space:nowrap;"
    )
    unit_style   = (
        "font-family:'JetBrains Mono',monospace;"
        "font-size:0.9rem;font-weight:600;color:#94A3B8;"
        "line-height:1;white-space:nowrap;"
        "align-self:flex-end;padding-bottom:3px;margin-left:2px;"
    )
    row_style    = "display:flex;align-items:baseline;gap:0;margin-bottom:5px;flex-wrap:nowrap;"
    sub_style    = "font-size:0.68rem;color:#64748B;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"
    delta_color  = "#10B981" if delta_pos else "#EF4444"
    delta_style  = f"font-size:0.72rem;font-weight:600;color:{delta_color};margin-top:4px;display:block;"
    badge_style  = (
        "position:absolute;top:8px;right:10px;"
        "font-size:0.55rem;font-weight:700;letter-spacing:0.1em;"
        "color:#F59E0B;text-transform:uppercase;"
        "background:rgba(245,158,11,0.12);"
        "border:1px solid rgba(245,158,11,0.3);"
        "border-radius:4px;padding:1px 5px;"
    )

    badge_html = f'<span style="{badge_style}">filtered</span>' if is_filtered else ""
    sub_html   = f'<div style="{sub_style}">{sub}</div>'        if sub          else ""
    arrow      = "▲" if delta_pos else "▼"
    delta_html = f'<span style="{delta_style}">{arrow} {delta}</span>' if delta else ""

    if isinstance(value, tuple):
        num, unit = value
        unit_part  = f'<span style="{unit_style}">{unit}</span>' if unit else ""
        value_html = f'<div style="{row_style}"><span style="{num_style}">{num}</span>{unit_part}</div>'
    else:
        value_html = f'<div style="{num_style};margin-bottom:5px;">{value}</div>'

    return (
        f'<div style="{card_style}">'
        f'{badge_html}'
        f'<div style="{label_style}">{icon} {label}</div>'
        f'{value_html}'
        f'{sub_html}'
        f'{delta_html}'
        f'</div>'
    )


# ═══════════════════════════════════════════════════════════════════════
#  TABS
# ═══════════════════════════════════════════════════════════════════════
tabs = st.tabs([
    "📊  Executive Overview",
    "👥  Customer Intelligence",
    "📦  Product & Category",
    "🌍  Regional Analytics",
    "🤖  ML Risk Engine",
    "🛠️  Discount Simulator",
])


# ╔══════════════════════════════════════════════════════════════════════
#  TAB 1 — EXECUTIVE OVERVIEW
# ╚══════════════════════════════════════════════════════════════════════
with tabs[0]:
    # ══════════════════════════════════════════════════════════════════
    #  EXACT KPI COMPUTATION — priority router
    #  Three filter types each have a pre-aggregated parquet that covers
    #  the FULL dataset (not the sample).  We query those directly so
    #  filtered KPIs are always 100 % accurate.
    #
    #  Priority:
    #    1. Category filter  → category_agg  (exact per-category totals)
    #    2. Market filter    → market_agg    (exact per-market totals)
    #    3. Segment filter   → segmented_customers (exact per-segment)
    #    4. No filter        → macro_kpis.json  (pre-computed globals)
    #
    #  If multiple filter types are active simultaneously we fall back to
    #  the ui_sample but scale the result up by the inverse sample ratio
    #  so it is at least proportionally correct and clearly labelled.
    # ══════════════════════════════════════════════════════════════════

    _disc_leak_pct = kpis.get("discount_impact_ratio_pct", 0)   # always global
    _kpi_source    = "global"   # for the banner

    def _sum_cols(df, rev_col, prof_col, rows=None):
        """Safe column sum on an optional row mask."""
        sub = df if rows is None else df[rows]
        r = sub[rev_col].sum()  if rev_col  in sub.columns else 0
        p = sub[prof_col].sum() if prof_col in sub.columns else 0
        return r, p

    if not filter_active:
        # ── No filters: use pre-computed JSON globals (fastest, exact) ──
        _rev   = kpis.get("total_revenue_usd", 0)
        _prof  = kpis.get("total_profit_usd",  0)
        _marg  = kpis.get("profit_margin_pct", 0)
        _aov   = kpis.get("average_order_value_usd", 0)
        _ncust = kpis.get("n_unique_customers", 0)
        _nord  = kpis.get("n_orders", 0)
        _kpi_source = "global"

    elif sel_cats and not sel_segs and not sel_mkts:
        # ── Category-only filter → category_agg.parquet (exact) ──
        df_c = D["df_cat"]
        mask = df_c["Category Name"].isin(sel_cats) if "Category Name" in df_c.columns else pd.Series(True, index=df_c.index)
        _rev, _prof = _sum_cols(df_c, "Total_Sales", "Total_Profit", mask)
        _marg  = (_prof / _rev * 100) if _rev else 0
        _ncust = 0   # not available at category level
        _nord  = int(df_c[mask]["Order_Count"].sum()) if "Order_Count" in df_c.columns else 0
        _aov   = (_rev / _nord)  if _nord else 0
        _kpi_source = "category_agg (exact)"

    elif sel_mkts and not sel_segs and not sel_cats:
        # ── Market-only filter → market_agg.parquet (exact) ──
        df_m = D["df_market"]
        mask = df_m["Market"].isin(sel_mkts) if "Market" in df_m.columns else pd.Series(True, index=df_m.index)
        _rev, _prof = _sum_cols(df_m, "Total_Sales", "Total_Profit", mask)
        _marg  = (_prof / _rev * 100) if _rev else 0
        _ncust = 0
        _nord  = int(df_m[mask]["Order_Count"].sum()) if "Order_Count" in df_m.columns else 0
        _aov   = (_rev / _nord) if _nord else 0
        _kpi_source = "market_agg (exact)"

    elif sel_segs and not sel_cats and not sel_mkts:
        # ── Segment-only filter → segmented_customers.parquet (exact) ──
        df_s = D["df_seg"] if not D["df_seg"].empty else D["df_cust"]
        seg_col = "Customer Segment" if "Customer Segment" in df_s.columns else None
        if seg_col:
            mask = df_s[seg_col].isin(sel_segs)
        else:
            mask = pd.Series(True, index=df_s.index)
        _rev, _prof = _sum_cols(df_s, "Total_Sales", "Total_Profit", mask)
        _marg  = (_prof / _rev * 100) if _rev else 0
        _ncust = int(mask.sum())
        _nord  = int(df_s[mask]["Order_Count"].sum()) if "Order_Count" in df_s.columns else 0
        _aov   = (_rev / _nord) if _nord else 0
        _kpi_source = "segment_agg (exact)"

    else:
        # ── Multi-dimension filter: scale sample up to full-dataset estimate ──
        # sample_ratio = how many rows the sample is vs full dataset
        _sample_n   = len(D["df_base"])
        _full_n     = kpis.get("n_orders", _sample_n)
        _scale      = _full_n / _sample_n if _sample_n else 1.0

        _rev_s  = filtered["Sales"].sum()                 if "Sales" in filtered.columns else 0
        _prof_s = filtered["Order Profit Per Order"].sum() if "Order Profit Per Order" in filtered.columns else 0
        _rev    = _rev_s  * _scale
        _prof   = _prof_s * _scale
        _marg   = (_prof / _rev * 100) if _rev else 0
        _nord   = int(len(filtered) * _scale)
        _aov    = filtered["Sales"].mean() if "Sales" in filtered.columns else 0
        _ncust  = 0   # can't reliably extrapolate unique count
        _kpi_source = f"sample ×{_scale:.1f} estimate"

    _disc_dollar = _rev * _disc_leak_pct / 100
    _fi = filter_active

    # ── Hero KPI row ──
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    kpi_cells = [
        (c1, "Gross Revenue",
         (f"${_rev/1e6:.2f}", "M"),
         f"{_nord:,} orders" if _nord else "full dataset", None, True, "blue", "💰"),
        (c2, "Net Profit",
         (f"${_prof/1e6:.2f}", "M"),
         "After all costs", None, _prof >= 0, "green", "📈"),
        (c3, "Profit Margin",
         (f"{_marg:.2f}", "%"),
         f"Undiscounted: {kpis.get('margin_zero_discount_pct',0):.2f}%",
         None, True, "cyan", "📊"),
        (c4, "Discount Leak",
         (f"{_disc_leak_pct:.2f}", "%"),
         f"${_disc_dollar:,.0f} margin lost",
         None, False, "red", "🔻"),
        (c5, "Avg Order Value",
         (f"${_aov:.0f}", ""),
         "Per transaction", None, True, "violet", "🛒"),
        (c6, "Unique Customers",
         (f"{_ncust:,}" if _ncust else "—", ""),
         "From aggregation" if _fi else f"Bleeders: {insights.get('n_bleeders',0)}",
         None, True, "amber", "👥"),
    ]
    for col, label, val, sub, delta, pos, color, icon in kpi_cells:
        with col:
            st.markdown(
                kpi_card(label, val, sub, delta, pos, color, icon, is_filtered=_fi),
                unsafe_allow_html=True
            )

    # ── Filter accuracy banner ──
    if filter_active:
        is_exact   = "agg (exact)" in _kpi_source or "segment_agg" in _kpi_source
        bstyle     = "success" if is_exact else "warning"
        icon_b     = "✅" if is_exact else "⚠️"
        accuracy   = "exact — drawn from full-dataset aggregates" if is_exact \
                     else "estimated — multiple filter dimensions require sample scaling"
        st.markdown(f"""
        <div style="background:{'rgba(16,185,129,0.08)' if is_exact else 'rgba(245,158,11,0.08)'};
                    border:1px solid {'rgba(16,185,129,0.3)' if is_exact else 'rgba(245,158,11,0.3)'};
                    border-left:4px solid {'#10B981' if is_exact else '#F59E0B'};
                    border-radius:8px;padding:10px 16px;margin-top:10px;font-size:0.78rem;">
        {icon_b} <b>Filter active</b> — KPIs are <b>{accuracy}</b>.
        Source: <code>{_kpi_source}</code>.
        Discount Leak % always reflects the global dataset.
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    # ── Automated Intelligence Alerts ──
    st.markdown('<div class="section-title">🔔 Automated Intelligence Alerts</div>', unsafe_allow_html=True)
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        st.markdown(f"""
        <div class="alert-warning">
        <b>⚡ Pareto Concentration</b><br>
        Only <b>{insights.get('pareto_pct',0):.1f}%</b> of customers drive 80% of profits.
        Portfolio is highly concentrated — top customers need retention priority.
        </div>""", unsafe_allow_html=True)
    with ac2:
        st.markdown(f"""
        <div class="alert-critical">
        <b>🚨 Loss-Making Customers</b><br>
        <b>{insights.get('n_bleeders',0)}</b> high-volume accounts operate at <b>negative margin</b>.
        Immediate pricing review required for these accounts.
        </div>""", unsafe_allow_html=True)
    with ac3:
        corr = insights.get('discount_profit_correlation', 0)
        st.markdown(f"""
        <div class="alert-info">
        <b>📉 Discount–Profit Correlation</b><br>
        Discount rate correlates <b>{corr:.3f}</b> with profit ratio.
        Every 10% discount increase erodes margin — pricing discipline critical.
        </div>""", unsafe_allow_html=True)

    # ── Segment Discount Elasticity ──
    st.markdown('<div class="section-title">📐 Segment Discount Elasticity</div>', unsafe_allow_html=True)
    elast = kpis.get("segment_discount_elasticity", {})
    if elast:
        el_col1, el_col2 = st.columns([2,1])
        with el_col1:
            el_df = pd.DataFrame(list(elast.items()), columns=["Segment","Elasticity"])
            fig_el = go.Figure(go.Bar(
                x=el_df["Segment"], y=el_df["Elasticity"],
                marker={
                    "color": [PALETTE["red"] if v < -0.065 else PALETTE["amber"] if v < -0.060 else PALETTE["green"]
                           for v in el_df["Elasticity"]],
                    "line": {"width": 0}
                },
                text=[f"{v:.4f}" for v in el_df["Elasticity"]],
                textposition="outside"
            ))
            fig_el.update_layout(
                title="Discount Elasticity by Segment (lower = more sensitive)",
                yaxis_title="Δ Profit / Δ Discount Rate",
                template=DARK_TEMPLATE, height=300,
                paper_bgcolor="#0D1426", plot_bgcolor="#0D1426"
            )
            st.plotly_chart(fig_el, use_container_width=True)
        with el_col2:
            st.markdown("""
            <div class="alert-info" style="margin-top:40px">
            <b>Reading the chart</b><br><br>
            A more negative value means discounts damage that segment's margin more severely.<br><br>
            <span class="insight-pill pill-danger">Consumer −0.069</span> most sensitive<br>
            <span class="insight-pill pill-warning">Corporate −0.064</span> moderate<br>
            <span class="insight-pill pill-success">Home Office −0.061</span> most resilient
            </div>""", unsafe_allow_html=True)

    # ── Revenue vs Profit ──
    st.markdown('<div class="section-title">📈 Revenue & Profit by Market</div>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)

    with col_a:
        if not D["df_market"].empty:
            mkt = D["df_market"].copy()
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(
                x=mkt["Market"], y=mkt["Total_Sales"],
                name="Revenue", marker_color=PALETTE["blue"],
                marker_line_width=0, opacity=0.85
            ), secondary_y=False)
            fig.add_trace(go.Scatter(
                x=mkt["Market"], y=mkt["Total_Profit"],
                name="Profit", mode="lines+markers",
                line={"color": PALETTE["green"], "width": 2.5},
                marker={"size": 8, "symbol": "circle"}
            ), secondary_y=True)
            fig.update_layout(
                title="Market Revenue vs Profit",
                template=DARK_TEMPLATE, height=380,
                paper_bgcolor="#0D1426", plot_bgcolor="#0D1426",
                legend={"orientation": "h", "y": -0.15}
            )
            fig.update_yaxes(title_text="Revenue ($)", secondary_y=False)
            fig.update_yaxes(title_text="Profit ($)", secondary_y=True,
                             showgrid=False, color=PALETTE["green"])
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        if "Order Profit Per Order" in filtered.columns:
            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=filtered["Order Profit Per Order"], nbinsx=60,
                marker_color=PALETTE["blue"], opacity=0.75,
                name="All Orders"
            ))
            # Negative profit shading
            loss_data = filtered[filtered["Order Profit Per Order"] < 0]["Order Profit Per Order"]
            fig.add_trace(go.Histogram(
                x=loss_data, nbinsx=30,
                marker_color=PALETTE["red"], opacity=0.8,
                name="Loss Orders"
            ))
            fig.add_vline(x=0, line_dash="dash", line_color=PALETTE["red"],
                          line_width=2, annotation_text="Break-Even",
                          annotation_font_color=PALETTE["red"])
            fig.update_layout(
                title="Order Profitability Distribution",
                xaxis_title="Profit per Order ($)",
                barmode="overlay",
                template=DARK_TEMPLATE, height=380,
                paper_bgcolor="#0D1426", plot_bgcolor="#0D1426",
                legend={"orientation": "h", "y": -0.15}
            )
            pct_loss = (filtered["Order Profit Per Order"] < 0).mean() * 100
            st.plotly_chart(fig, use_container_width=True)
            st.markdown(f"""
            <div class="alert-{'critical' if pct_loss > 20 else 'warning'}">
            <b>{pct_loss:.1f}%</b> of orders in current view are loss-making
            {'— CRITICAL threshold exceeded' if pct_loss > 20 else ''}
            </div>""", unsafe_allow_html=True)

    # ── Margin composition waterfall ──
    st.markdown('<div class="section-title">🏗️ Margin Composition</div>', unsafe_allow_html=True)
    rev   = kpis.get("total_revenue_usd", 0)
    prof  = kpis.get("total_profit_usd", 0)
    disc_leak = kpis.get("discount_impact_ratio_pct", 0) / 100 * rev
    cost  = rev - prof - disc_leak

    wf_fig = go.Figure(go.Waterfall(
        name="Margin Bridge",
        orientation="v",
        measure=["absolute","relative","relative","total"],
        x=["Gross Revenue","Costs & COGS","Discount Leak","Net Profit"],
        y=[rev, -cost, -disc_leak, 0],
        connector={"line": {"color": "#1E2D4A", "width": 1}},
        increasing={"marker_color": PALETTE["green"]},
        decreasing={"marker_color": PALETTE["red"]},
        totals={"marker_color": PALETTE["blue"]},
        text=[f"${rev/1e6:.2f}M", f"-${cost/1e6:.2f}M",
              f"-${disc_leak/1e6:.2f}M", f"${prof/1e6:.2f}M"],
        textposition="outside"
    ))
    wf_fig.update_layout(
        title="P&L Waterfall — Revenue to Net Profit",
        template=DARK_TEMPLATE, height=360,
        paper_bgcolor="#0D1426", plot_bgcolor="#0D1426"
    )
    st.plotly_chart(wf_fig, use_container_width=True)

    if filter_active:
        st.markdown(f"""
        <div class="alert-info">
        🔍 Filters active — showing <b>{n_filtered:,}</b> sample records
        matching your selection.
        </div>""", unsafe_allow_html=True)


# ╔══════════════════════════════════════════════════════════════════════
#  TAB 2 — CUSTOMER INTELLIGENCE
# ╚══════════════════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown("""
    <div class="tab-hero">
        <h2>👥 Customer Intelligence</h2>
        <p>Revenue–profit matrix · RFM segmentation · CLV tiers · churn risk scoring</p>
    </div>""", unsafe_allow_html=True)

    seg_df = D["df_seg"] if not D["df_seg"].empty else D["df_cust"]
    color_col = "Segment_Class" if "Segment_Class" in seg_df.columns else "Customer_Value_Index"

    # ── Value Matrix ──
    st.markdown('<div class="section-title">💎 Customer Revenue vs Profit Matrix</div>', unsafe_allow_html=True)
    col1, col2 = st.columns([3,1])
    with col1:
        size_col = "Order_Count" if "Order_Count" in seg_df.columns else None
        hover_cols = {c: True for c in ["Customer Id","Segment_Class","Order_Count"]
                      if c in seg_df.columns}
        fig = px.scatter(
            seg_df, x="Total_Sales", y="Total_Profit",
            color=color_col,
            size=size_col,
            hover_data=hover_cols,
            title="Customer Quadrant — Revenue vs Profit",
            color_discrete_sequence=list(PALETTE.values()),
            opacity=0.60,
            template=DARK_TEMPLATE, height=500
        )
        fig.add_hline(y=0, line_dash="dash", line_color=PALETTE["red"],
                      line_width=1.5, annotation_text="Profit Zero-Line",
                      annotation_font_color=PALETTE["red"])
        fig.add_vline(x=seg_df["Total_Sales"].median(), line_dash="dot",
                      line_color=PALETTE["amber"], line_width=1,
                      annotation_text="Median Sales",
                      annotation_font_color=PALETTE["amber"])
        fig.update_layout(paper_bgcolor="#0D1426", plot_bgcolor="#0D1426")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "Segment_Class" in seg_df.columns:
            sc = seg_df["Segment_Class"].value_counts().reset_index()
            sc.columns = ["Segment","Count"]
            fig2 = px.pie(sc, names="Segment", values="Count",
                          title="Segment Split",
                          color_discrete_sequence=list(PALETTE.values()),
                          hole=0.55)
            fig2.update_traces(textinfo="percent+label", textfont_size=10)
            fig2.update_layout(
                template=DARK_TEMPLATE, height=280,
                paper_bgcolor="#0D1426",
                showlegend=False,
                margin={"t": 40,"b": 0,"l": 0,"r": 0}
            )
            st.plotly_chart(fig2, use_container_width=True)

        st.markdown("**🏆 Top Customers by Profit**")
        top_cols = ["Customer Id","Total_Sales","Total_Profit"]
        top_cols = [c for c in top_cols if c in seg_df.columns]
        top5 = seg_df.sort_values("Total_Profit", ascending=False).head(top_n_cust)[top_cols]
        if "Total_Profit" in top5.columns:
            top5["Total_Profit"] = top5["Total_Profit"].map(lambda x: f"${x:,.0f}")
        if "Total_Sales" in top5.columns:
            top5["Total_Sales"] = top5["Total_Sales"].map(lambda x: f"${x:,.0f}")
        st.dataframe(top5, hide_index=True, use_container_width=True, height=200)

        st.markdown("**🚨 Bottom Customers (Loss)**")
        bot5 = seg_df.sort_values("Total_Profit").head(5)[["Customer Id","Total_Profit"]]
        bot5["Total_Profit"] = bot5["Total_Profit"].map(lambda x: f"${x:,.0f}")
        st.dataframe(bot5, hide_index=True, use_container_width=True)

    # ── RFM ──
    if not D["df_rfm"].empty and "RFM_Segment" in D["df_rfm"].columns:
        st.markdown('<div class="section-title">🎯 RFM Segmentation Analysis</div>', unsafe_allow_html=True)
        rfm = D["df_rfm"]
        rfm_c1, rfm_c2 = st.columns(2)

        with rfm_c1:
            rfm_count = rfm["RFM_Segment"].value_counts().reset_index()
            rfm_count.columns = ["Segment","Count"]
            # Color map by segment type
            color_map = {
                "At Risk":           PALETTE["red"],
                "Lost":              "#6B7280",
                "Potential Loyalist":PALETTE["amber"],
                "Champions":         PALETTE["green"],
                "Loyal":             PALETTE["blue"],
                "New Customers":     PALETTE["cyan"],
                "Hibernating":       PALETTE["violet"],
            }
            fig_rfm = px.bar(rfm_count, x="Count", y="Segment", orientation="h",
                             color="Segment",
                             color_discrete_map=color_map,
                             title="RFM Segment Distribution",
                             text="Count")
            fig_rfm.update_traces(textposition="outside", textfont_size=11)
            fig_rfm.update_layout(
                template=DARK_TEMPLATE, height=380,
                paper_bgcolor="#0D1426", plot_bgcolor="#0D1426",
                showlegend=False,
                yaxis={"categoryorder": "total ascending"}
            )
            st.plotly_chart(fig_rfm, use_container_width=True)

        with rfm_c2:
            dist = insights.get("rfm_distribution", {})
            st.markdown("**📌 RFM Intelligence Summary**")
            total_cust = kpis.get("n_unique_customers", 1)
            for seg, cnt in dist.items():
                pct = cnt/total_cust*100
                color_key = "danger" if seg in ("At Risk","Lost") else \
                            "warning" if seg == "Potential Loyalist" else "success"
                st.markdown(f"""
                <div class="alert-{'critical' if color_key=='danger' else color_key}">
                <b>{seg}</b>: {cnt:,} customers ({pct:.1f}% of base)
                </div>""", unsafe_allow_html=True)

            st.markdown(f"""
            <div class="alert-warning" style="margin-top:12px">
            <b>⚠️ At-Risk + Lost = {sum(dist.values()):,} customers</b><br>
            These accounts represent significant revenue recovery opportunity.
            </div>""", unsafe_allow_html=True)

    # ── Customer LTV ──
    if not D["df_ltv"].empty and "LTV_Probability" in D["df_ltv"].columns:
        st.markdown('<div class="section-title">⚠️ Customer LTV Radar</div>', unsafe_allow_html=True)
        churn = D["df_ltv"].copy()
        ch1, ch2 = st.columns(2)

        with ch1:
            # Distribution
            fig_ch = go.Figure()
            fig_ch.add_trace(go.Histogram(
                x=churn["LTV_Probability"], nbinsx=40,
                marker_color=PALETTE["red"], opacity=0.75, name="Churn Prob"
            ))
            fig_ch.add_vline(x=0.5, line_dash="dash", line_color=PALETTE["amber"],
                             annotation_text="50% Risk Line",
                             annotation_font_color=PALETTE["amber"])
            fig_ch.update_layout(
                title="Churn Probability Distribution",
                xaxis_title="Churn Probability",
                template=DARK_TEMPLATE, height=320,
                paper_bgcolor="#0D1426", plot_bgcolor="#0D1426"
            )
            st.plotly_chart(fig_ch, use_container_width=True)

        with ch2:
            top_churn = churn.sort_values("LTV_Probability", ascending=False).head(top_n_cust)
            show_cols = [c for c in ["Customer Id","Total_Revenue","Order_Count","LTV_Probability"]
                         if c in top_churn.columns]
            top_churn = top_churn[show_cols].copy()
            if "LTV_Probability" in top_churn.columns:
                top_churn["LTV_Probability"] = top_churn["LTV_Probability"].map(lambda x: f"{x:.1%}")
            if "Total_Revenue" in top_churn.columns:
                top_churn["Total_Revenue"] = top_churn["Total_Revenue"].map(lambda x: f"${x:,.0f}")
            st.markdown(f"**🚨 Top {top_n_cust} Highest Churn-Risk Customers**")
            st.dataframe(top_churn, hide_index=True, use_container_width=True, height=320)

        high_risk_count = (churn["LTV_Probability"] >= 0.5).sum()
        if "Total_Revenue" in churn.columns:
            revenue_at_risk = churn[churn["LTV_Probability"] >= 0.5]["Total_Revenue"].sum()
            st.markdown(f"""
            <div class="alert-critical">
            🚨 <b>{high_risk_count:,} customers</b> have ≥50% churn probability,
            representing <b>${revenue_at_risk:,.0f}</b> of revenue at risk.
            Immediate outreach programme recommended.
            </div>""", unsafe_allow_html=True)


# ╔══════════════════════════════════════════════════════════════════════
#  TAB 3 — PRODUCT & CATEGORY
# ╚══════════════════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown("""
    <div class="tab-hero">
        <h2>📦 Product & Category Intelligence</h2>
        <p>Category margins · ABC classification · health scoring · loss-maker diagnostics</p>
    </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if not D["df_cat"].empty:
            cat = D["df_cat"].copy()
            fig = px.bar(
                cat.sort_values("Total_Profit", ascending=True).tail(15),
                y="Category Name", x="Total_Profit", orientation="h",
                color="Total_Profit",
                color_continuous_scale=[[0,"#EF4444"],[0.5,"#F59E0B"],[1,"#10B981"]],
                title="Category Profit Ranking (Top 15)",
                text="Total_Profit"
            )
            fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
            fig.update_layout(
                template=DARK_TEMPLATE, height=480,
                paper_bgcolor="#0D1426", plot_bgcolor="#0D1426",
                coloraxis_showscale=False,
                yaxis={"categoryorder": "total ascending"}
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if not D["df_product"].empty:
            prod = D["df_product"].copy()
            loss_p = prod[prod["Total_Profit"] < 0].sort_values("Total_Profit").head(12)
            if not loss_p.empty:
                fig = px.bar(
                    loss_p, y="Product Name", x="Total_Profit", orientation="h",
                    title="⚠️ Loss-Making Products",
                    color_discrete_sequence=[PALETTE["red"]],
                    text="Total_Profit"
                )
                fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
                fig.update_layout(
                    template=DARK_TEMPLATE, height=480,
                    paper_bgcolor="#0D1426", plot_bgcolor="#0D1426",
                    yaxis={"categoryorder": "total descending"}
                )
                st.plotly_chart(fig, use_container_width=True)
                st.markdown(f"""
                <div class="alert-critical">
                🚨 <b>{len(loss_p)} products</b> are loss-making.
                Total loss: <b>${loss_p['Total_Profit'].sum():,.0f}</b>
                </div>""", unsafe_allow_html=True)

    # ── ABC ──
    if not D["df_abc"].empty and "ABC_Class" in D["df_abc"].columns:
        st.markdown('<div class="section-title">📊 ABC Inventory Classification</div>', unsafe_allow_html=True)
        abc = D["df_abc"].copy()
        abc_c1, abc_c2 = st.columns([1,2])

        with abc_c1:
            abc_sum = abc.groupby("ABC_Class")["Total_Profit"].sum().reset_index()
            color_map_abc = {
                "A (Top 70%)":      PALETTE["green"],
                "B (70–90%)":       PALETTE["amber"],
                "C (Bottom 10%)":   PALETTE["red"],
            }
            fig_abc = px.pie(abc_sum, names="ABC_Class", values="Total_Profit",
                             color="ABC_Class",
                             color_discrete_map=color_map_abc,
                             title="Profit by ABC Class",
                             hole=0.55)
            fig_abc.update_traces(textinfo="percent+label", textfont_size=11)
            fig_abc.update_layout(
                template=DARK_TEMPLATE, height=340,
                paper_bgcolor="#0D1426",
                showlegend=False,
                margin={"t": 40,"b": 0,"l": 0,"r": 0}
            )
            st.plotly_chart(fig_abc, use_container_width=True)

        with abc_c2:
            for cls, color in [("A (Top 70%)", "success"), ("B (70–90%)", "warning"), ("C (Bottom 10%)", "critical")]:
                sub = abc[abc["ABC_Class"] == cls]
                if not sub.empty:
                    top_p = sub.nlargest(3, "Total_Profit")["Product Name"].tolist()
                    st.markdown(f"""
                    <div class="alert-{color}">
                    <b>Class {cls}</b> — {len(sub)} products | Profit: ${sub['Total_Profit'].sum():,.0f}<br>
                    Top: {', '.join(top_p[:3])}
                    </div>""", unsafe_allow_html=True)

    # ── Category Health ──
    if not D["df_cat_h"].empty and "Health_Score" in D["df_cat_h"].columns:
        st.markdown('<div class="section-title">🏥 Category Health Score</div>', unsafe_allow_html=True)
        cat_h = D["df_cat_h"].sort_values("Health_Score")
        fig_h = go.Figure()
        colors = [PALETTE["red"] if s < 33 else PALETTE["amber"] if s < 66 else PALETTE["green"]
                  for s in cat_h["Health_Score"]]
        fig_h.add_trace(go.Bar(
            y=cat_h["Category Name"], x=cat_h["Health_Score"],
            orientation="h",
            marker={"color": colors, "line": {"width": 0}},
            text=[f"{s:.1f}" for s in cat_h["Health_Score"]],
            textposition="outside"
        ))
        fig_h.add_vline(x=33, line_dash="dash", line_color=PALETTE["red"], line_width=1)
        fig_h.add_vline(x=66, line_dash="dash", line_color=PALETTE["amber"], line_width=1)
        fig_h.update_layout(
            title="Category Health Score (Margin × Volume composite)",
            xaxis_title="Health Score (0–100)",
            template=DARK_TEMPLATE, height=500,
            paper_bgcolor="#0D1426", plot_bgcolor="#0D1426",
            yaxis={"categoryorder": "total ascending"}
        )
        st.plotly_chart(fig_h, use_container_width=True)


# ╔══════════════════════════════════════════════════════════════════════
#  TAB 4 — REGIONAL ANALYTICS
# ╚══════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown("""
    <div class="tab-hero">
        <h2>🌍 Regional Analytics</h2>
        <p>Market treemaps · regional margin benchmarks · shipping mode profitability</p>
    </div>""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if not D["df_market"].empty:
            fig = px.treemap(
                D["df_market"], path=["Market"], values="Total_Sales",
                color="Total_Profit",
                color_continuous_scale=[[0,"#EF4444"],[0.5,"#F59E0B"],[1,"#10B981"]],
                title="Revenue Treemap — colour = net profit",
            )
            fig.update_traces(textfont_size=14, marker_line_width=2,
                              marker_line_color="#0D1426")
            fig.update_layout(
                template=DARK_TEMPLATE, height=400,
                paper_bgcolor="#0D1426"
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if not D["df_region"].empty:
            region = D["df_region"].sort_values("Profit_Margin_pct")
            fig = go.Figure()
            colors = [PALETTE["red"] if m < 10 else PALETTE["amber"] if m < 20 else PALETTE["green"]
                      for m in region["Profit_Margin_pct"]]
            fig.add_trace(go.Bar(
                y=region["Order Region"], x=region["Profit_Margin_pct"],
                orientation="h",
                marker={"color": colors, "line": {"width": 0}},
                text=[f"{m:.1f}%" for m in region["Profit_Margin_pct"]],
                textposition="outside"
            ))
            fig.add_vline(x=kpis.get("profit_margin_pct",0), line_dash="dash",
                          line_color=PALETTE["blue"], line_width=2,
                          annotation_text=f"Global Avg {kpis.get('profit_margin_pct',0):.1f}%",
                          annotation_font_color=PALETTE["blue"])
            fig.update_layout(
                title="Profit Margin % by Order Region",
                xaxis_title="Profit Margin (%)",
                template=DARK_TEMPLATE, height=400,
                paper_bgcolor="#0D1426", plot_bgcolor="#0D1426",
                yaxis={"categoryorder": "total ascending"}
            )
            st.plotly_chart(fig, use_container_width=True)

    # -- Market KPI table --
    if not D["df_market"].empty:
        st.markdown('<div class="section-title">📋 Market Performance Scorecard</div>', unsafe_allow_html=True)
        mkt_disp = D["df_market"].copy()
        if "Profit_Margin_pct" not in mkt_disp.columns and "Total_Sales" in mkt_disp.columns:
            mkt_disp["Profit_Margin_pct"] = mkt_disp["Total_Profit"] / mkt_disp["Total_Sales"] * 100
        mkt_disp = mkt_disp.sort_values("Profit_Margin_pct", ascending=False) \
                            if "Profit_Margin_pct" in mkt_disp.columns \
                            else mkt_disp.sort_values("Total_Sales", ascending=False)
        for col in ["Total_Sales", "Total_Profit"]:
            if col in mkt_disp.columns:
                mkt_disp[col] = mkt_disp[col].map(lambda x: f"${x:,.0f}")
        if "Profit_Margin_pct" in mkt_disp.columns:
            mkt_disp["Profit_Margin_pct"] = mkt_disp["Profit_Margin_pct"].map(lambda x: f"{x:.2f}%")
        st.dataframe(mkt_disp, hide_index=True, use_container_width=True)

    # -- Shipping Mode --
    if not D["df_ship"].empty:
        st.markdown('<div class="section-title">🚚 Shipping Mode Intelligence</div>', unsafe_allow_html=True)
        ship = D["df_ship"].copy()
        sh1, sh2 = st.columns(2)

        with sh1:
            fig_s = go.Figure()
            fig_s.add_trace(go.Bar(
                name="Revenue",
                x=ship["Shipping Mode"], y=ship["Total_Sales"],
                marker_color=PALETTE["blue"], opacity=0.85
            ))
            fig_s.add_trace(go.Bar(
                name="Profit",
                x=ship["Shipping Mode"], y=ship["Total_Profit"],
                marker_color=PALETTE["green"], opacity=0.85
            ))
            fig_s.update_layout(
                barmode="group",
                title="Revenue vs Profit by Shipping Mode",
                template=DARK_TEMPLATE, height=360,
                paper_bgcolor="#0D1426", plot_bgcolor="#0D1426"
            )
            st.plotly_chart(fig_s, use_container_width=True)

        with sh2:
            if "Total_Sales" in ship.columns:
                ship["Margin_pct"] = ship["Total_Profit"] / ship["Total_Sales"] * 100
                fig_m = px.bar(ship, x="Shipping Mode", y="Margin_pct",
                               title="Margin % by Shipping Mode",
                               color="Margin_pct",
                               color_continuous_scale=[[0,"#EF4444"],[0.5,"#F59E0B"],[1,"#10B981"]],
                               text=[f"{m:.1f}%" for m in ship["Margin_pct"]])
                fig_m.update_traces(textposition="outside")
                fig_m.update_layout(
                    template=DARK_TEMPLATE, height=360,
                    paper_bgcolor="#0D1426", plot_bgcolor="#0D1426",
                    coloraxis_showscale=False
                )
                st.plotly_chart(fig_m, use_container_width=True)

    st.markdown("""
    <div class="alert-info">
    🗺️ <b>Interactive Geo-Maps available:</b> Open
    <code>processed_data/analytics/spatial/maps/plotly_profit_map.html</code>
    and <code>folium_leak_detector.html</code> in your browser for full geographic analysis.
    </div>""", unsafe_allow_html=True)


# ╔══════════════════════════════════════════════════════════════════════
#  TAB 5 — ML RISK ENGINE
# ╚══════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.markdown("""
    <div class="tab-hero">
        <h2>🤖 ML Risk Engine</h2>
        <p>GBM + Optuna HPO · SHAP/PFI explainability · OOT validation · Calibrated probabilities · MLflow tracked</p>
    </div>""", unsafe_allow_html=True)

    # ── Model Scorecard KPIs (8 cards) ──
    st.markdown('<div class="section-title">🏅 Model Performance Scorecard</div>', unsafe_allow_html=True)

    auc_m     = ml_report.get("margin_risk_auc", 0)
    auc_c     = ml_report.get("churn_risk_auc", 0)
    cv_m      = ml_report.get("margin_risk_cv_mean", 0)
    cv_m_std  = ml_report.get("margin_risk_cv_std", 0)
    cv_c      = ml_report.get("churn_risk_cv_mean", 0)
    cv_c_std  = ml_report.get("churn_risk_cv_std", 0)
    oot_m     = ml_report.get("margin_risk_oot_auc", auc_m)
    oot_c     = ml_report.get("churn_risk_oot_auc", auc_c)
    brier_m   = ml_report.get("margin_risk_brier_score", 0)
    brier_c   = ml_report.get("churn_risk_brier_score", 0)
    hpo_fw    = ml_report.get("hpo_framework", "GBM")
    expl_fw   = ml_report.get("explainability", "PFI")
    mlf_ok    = ml_report.get("mlflow_tracked", False)
    pipe_ver  = ml_report.get("pipeline_version", "v1")

    auc_m_color = "green" if auc_m > 0.80 else "amber" if auc_m > 0.65 else "red"
    auc_c_color = "green" if 0.65 < auc_c < 0.99 else "amber" if auc_c > 0.55 else "red"

    sc1, sc2, sc3, sc4 = st.columns(4)
    sc5, sc6, sc7, sc8 = st.columns(4)

    sc1.markdown(kpi_card("Margin Risk AUC", (f"{auc_m:.4f}", ""),
                          f"OOT holdout | v{pipe_ver}",
                          None, auc_m > 0.75, auc_m_color, "🎯"), unsafe_allow_html=True)
    sc2.markdown(kpi_card("Margin CV Score", (f"{cv_m:.4f}", ""),
                          f"±{cv_m_std:.4f}  5-fold stratified",
                          None, cv_m > 0.75, "blue", "📊"), unsafe_allow_html=True)
    sc3.markdown(kpi_card("Customer LTV AUC", (f"{auc_c:.4f}", ""),
                          "OOT holdout | leak-free label",
                          None, 0.60 < auc_c < 0.99, auc_c_color, "🔮"), unsafe_allow_html=True)
    sc4.markdown(kpi_card("Churn CV Score", (f"{cv_c:.4f}", ""),
                          f"±{cv_c_std:.4f}  5-fold stratified",
                          None, cv_c > 0.65, "blue", "📊"), unsafe_allow_html=True)

    sc5.markdown(kpi_card("Margin Brier", (f"{brier_m:.4f}", ""),
                          "Lower = better calibration",
                          None, brier_m < 0.20, "cyan", "⚡"), unsafe_allow_html=True)
    sc6.markdown(kpi_card("Churn Brier", (f"{brier_c:.4f}", ""),
                          "Lower = better calibration",
                          None, brier_c < 0.25, "cyan", "⚡"), unsafe_allow_html=True)
    sc7.markdown(kpi_card("HPO Engine", hpo_fw,
                          "40 trials · TPE sampler",
                          None, True, "violet", "🧬"), unsafe_allow_html=True)
    sc8.markdown(kpi_card("Explainability", expl_fw,
                          f"MLflow: {'✅' if mlf_ok else '⚠ not logged'}",
                          None, True, "green", "🧠"), unsafe_allow_html=True)

    # ── Pipeline quality banners ──
    if auc_m > 0.80 and 0.60 < auc_c < 0.99:
        st.markdown(f"""
        <div class="alert-success">
        ✅ <b>Production-grade ML pipeline v{pipe_ver}</b> — Both models pass quality gates:
        Margin Risk AUC={auc_m:.4f} (target &gt; 0.80) ·
        Customer LTV AUC={auc_c:.4f} (target 0.65–0.95, no leakage).
        HPO: {hpo_fw} · Explainability: {expl_fw} · Calibration: CalibratedClassifierCV (isotonic)
        </div>""", unsafe_allow_html=True)
    elif auc_m < 0.60:
        st.markdown(f"""
        <div class="alert-warning">
        ⚠️ <b>Margin Risk AUC={auc_m:.4f}</b> — Run <code>python step6_ml_v2.py</code> to rebuild the ML pipeline.
        </div>""", unsafe_allow_html=True)
    if auc_c > 0.99:
        st.markdown("""
        <div class="alert-critical">
        🚨 <b>Customer LTV AUC = 1.0 indicates data leakage.</b>
        Run <code>python step6_ml_v2.py</code> to rebuild with the leak-free pipeline.
        </div>""", unsafe_allow_html=True)

    # ── Optuna Trial History ──
    optuna_m_path = Path("processed_data/ml/optuna_margin_trials.csv")
    optuna_c_path = Path("processed_data/ml/optuna_churn_trials.csv")

    if optuna_m_path.exists() or optuna_c_path.exists():
        st.markdown('<div class="section-title">🧬 Optuna HPO Trial History</div>', unsafe_allow_html=True)
        ot1, ot2 = st.columns(2)

        with ot1:
            if optuna_m_path.exists():
                try:
                    opt_m_df = pd.read_csv(optuna_m_path)
                    val_col = [c for c in opt_m_df.columns if 'value' in c.lower()]
                    if val_col:
                        opt_m_df['best_so_far'] = opt_m_df[val_col[0]].cummax()
                        fig_opt = go.Figure()
                        fig_opt.add_trace(go.Scatter(
                            x=opt_m_df.index, y=opt_m_df[val_col[0]],
                            mode="markers", marker={"color": PALETTE["blue"], "size": 5, "opacity": 0.5},
                            name="Trial AUC"
                        ))
                        fig_opt.add_trace(go.Scatter(
                            x=opt_m_df.index, y=opt_m_df["best_so_far"],
                            mode="lines", line={"color": PALETTE["green"], "width": 2.5},
                            name="Best So Far"
                        ))
                        fig_opt.update_layout(
                            title=f"Margin Risk HPO — Best AUC: {opt_m_df[val_col[0]].max():.4f}",
                            xaxis_title="Trial", yaxis_title="CV AUC (5-fold)",
                            template=DARK_TEMPLATE, height=320,
                            paper_bgcolor="#0D1426", plot_bgcolor="#0D1426",
                            legend={"orientation": "h", "y": -0.2}
                        )
                        st.plotly_chart(fig_opt, use_container_width=True)
                except Exception:
                    st.info("Optuna margin trial data unavailable.")

        with ot2:
            if optuna_c_path.exists():
                try:
                    opt_c_df = pd.read_csv(optuna_c_path)
                    val_col_c = [c for c in opt_c_df.columns if 'value' in c.lower()]
                    if val_col_c:
                        opt_c_df['best_so_far'] = opt_c_df[val_col_c[0]].cummax()
                        fig_opt_c = go.Figure()
                        fig_opt_c.add_trace(go.Scatter(
                            x=opt_c_df.index, y=opt_c_df[val_col_c[0]],
                            mode="markers", marker={"color": PALETTE["violet"], "size": 5, "opacity": 0.5},
                            name="Trial AUC"
                        ))
                        fig_opt_c.add_trace(go.Scatter(
                            x=opt_c_df.index, y=opt_c_df["best_so_far"],
                            mode="lines", line={"color": PALETTE["amber"], "width": 2.5},
                            name="Best So Far"
                        ))
                        fig_opt_c.update_layout(
                            title=f"Customer LTV HPO — Best AUC: {opt_c_df[val_col_c[0]].max():.4f}",
                            xaxis_title="Trial", yaxis_title="CV AUC (5-fold)",
                            template=DARK_TEMPLATE, height=320,
                            paper_bgcolor="#0D1426", plot_bgcolor="#0D1426",
                            legend={"orientation": "h", "y": -0.2}
                        )
                        st.plotly_chart(fig_opt_c, use_container_width=True)
                except Exception:
                    st.info("Optuna churn trial data unavailable.")

    # ── Feature Importance / SHAP ──
    st.markdown('<div class="section-title">🧠 Feature Importance (SHAP / Permutation)</div>', unsafe_allow_html=True)
    fi_col1, fi_col2 = st.columns(2)

    with fi_col1:
        fi_m_raw = ml_report.get("margin_risk_feature_importance", {})
        if fi_m_raw:
            fi_m_s  = pd.Series(fi_m_raw).sort_values(ascending=True)
            fi_m_df = fi_m_s.reset_index()
            fi_m_df.columns = ["Feature", "Importance"]
            method_label = "SHAP Mean |φ|" if ml_report.get("margin_risk_shap_available") else "Permutation Importance"
            fig_fim = go.Figure(go.Bar(
                y=fi_m_df["Feature"], x=fi_m_df["Importance"],
                orientation="h",
                marker={
                    "color": fi_m_df["Importance"],
                    "colorscale": [[0, PALETTE["blue"]], [1, PALETTE["violet"]]],
                    "line": {"width": 0}
                },
                text=[f"{v:.4f}" for v in fi_m_df["Importance"]],
                textposition="outside"
            ))
            fig_fim.update_layout(
                title=f"Margin Risk — {method_label}",
                xaxis_title=method_label,
                template=DARK_TEMPLATE, height=400,
                paper_bgcolor="#0D1426", plot_bgcolor="#0D1426"
            )
            st.plotly_chart(fig_fim, use_container_width=True)
            top_f = fi_m_s.index[-1]
            st.markdown(f"""
            <div class="alert-info">
            💡 <b>Top driver: {top_f}</b> — Highest influence on margin risk prediction.
            Focus discount controls and pricing reviews on this dimension first.
            </div>""", unsafe_allow_html=True)

    with fi_col2:
        fi_c_raw = ml_report.get("churn_risk_feature_importance", {})
        if fi_c_raw:
            fi_c_s  = pd.Series(fi_c_raw).sort_values(ascending=True)
            fi_c_df = fi_c_s.reset_index()
            fi_c_df.columns = ["Feature", "Importance"]
            fig_fic = go.Figure(go.Bar(
                y=fi_c_df["Feature"], x=fi_c_df["Importance"],
                orientation="h",
                marker={
                    "color": fi_c_df["Importance"],
                    "colorscale": [[0, PALETTE["amber"]], [1, PALETTE["red"]]],
                    "line": {"width": 0}
                },
                text=[f"{v:.4f}" for v in fi_c_df["Importance"]],
                textposition="outside"
            ))
            fig_fic.update_layout(
                title="Customer LTV — Feature Importance",
                xaxis_title="Importance Score",
                template=DARK_TEMPLATE, height=400,
                paper_bgcolor="#0D1426", plot_bgcolor="#0D1426"
            )
            st.plotly_chart(fig_fic, use_container_width=True)
            top_cf = fi_c_s.index[-1]
            st.markdown(f"""
            <div class="alert-info">
            💡 <b>Top churn driver: {top_cf}</b> — Customers with extreme values on this
            feature are most likely in the At Risk / Lost RFM cohort.
            </div>""", unsafe_allow_html=True)

    # ── High-Risk Orders ──
    if not D["df_margin"].empty and "Margin_Risk_Probability" in D["df_margin"].columns:
        st.markdown('<div class="section-title">🔴 High-Risk Orders</div>', unsafe_allow_html=True)
        mg1, mg2 = st.columns(2)

        with mg1:
            margin_df = D["df_margin"].copy()
            n_high = (margin_df["Margin_Risk_Probability"] >= risk_thresh).sum()
            fig_dist = go.Figure()
            fig_dist.add_trace(go.Histogram(
                x=margin_df["Margin_Risk_Probability"], nbinsx=50,
                marker_color=PALETTE["blue"], opacity=0.7, name="All Orders"
            ))
            high_r = margin_df[margin_df["Margin_Risk_Probability"] >= risk_thresh]
            fig_dist.add_trace(go.Histogram(
                x=high_r["Margin_Risk_Probability"], nbinsx=30,
                marker_color=PALETTE["red"], opacity=0.85, name="High Risk"
            ))
            fig_dist.add_vline(x=risk_thresh, line_dash="solid",
                               line_color=PALETTE["amber"], line_width=2.5,
                               annotation_text=f"Threshold {risk_thresh:.2f}",
                               annotation_font_color=PALETTE["amber"])
            fig_dist.update_layout(
                title=f"Margin Risk Distribution — {n_high:,} orders above threshold",
                barmode="overlay",
                template=DARK_TEMPLATE, height=360,
                paper_bgcolor="#0D1426", plot_bgcolor="#0D1426",
                legend={"orientation": "h", "y": -0.2}
            )
            st.plotly_chart(fig_dist, use_container_width=True)

        with mg2:
            high_risk = margin_df[margin_df["Margin_Risk_Probability"] >= risk_thresh] \
                            .sort_values("Margin_Risk_Probability", ascending=False).head(20)
            show = [c for c in ["Customer Id", "Margin_Risk_Probability",
                                "Order Item Discount Rate", "Order Profit Per Order",
                                "Is_Loss_Order"] if c in high_risk.columns]
            hr_disp = high_risk[show].copy()
            if "Margin_Risk_Probability" in hr_disp.columns:
                hr_disp["Margin_Risk_Probability"] = hr_disp["Margin_Risk_Probability"].map(lambda x: f"{x:.1%}")
            if "Order Item Discount Rate" in hr_disp.columns:
                hr_disp["Order Item Discount Rate"] = hr_disp["Order Item Discount Rate"].map(lambda x: f"{x:.1%}")
            if "Order Profit Per Order" in hr_disp.columns:
                hr_disp["Order Profit Per Order"] = hr_disp["Order Profit Per Order"].map(lambda x: f"${x:,.0f}")
            if "Is_Loss_Order" in hr_disp.columns:
                hr_disp["Is_Loss_Order"] = hr_disp["Is_Loss_Order"].map(lambda x: "🔴 Loss" if x == 1 else "✅ Profit")
            st.markdown(f"**Top 20 Highest-Risk Orders (≥ {risk_thresh:.0%})**")
            st.dataframe(hr_disp, hide_index=True, use_container_width=True, height=360)


# ╔══════════════════════════════════════════════════════════════════════
#  TAB 6 — DISCOUNT SIMULATOR
# ╚══════════════════════════════════════════════════════════════════════
with tabs[5]:
    st.markdown("""
    <div class="tab-hero">
        <h2>🛠️ Discount Policy Simulator</h2>
        <p>What-if analysis · policy violation detection · sensitivity table · margin recovery estimation</p>
    </div>""", unsafe_allow_html=True)

    if "Order Item Discount Rate" in filtered.columns and "Order Profit Per Order" in filtered.columns:
        cur_profit  = filtered["Order Profit Per Order"].sum()
        breach      = filtered[filtered["Order Item Discount Rate"] > disc_cap]
        n_breach    = len(breach)
        breach_pct  = n_breach / max(len(filtered), 1) * 100
        recovered   = (breach["Sales"] * (breach["Order Item Discount Rate"] - disc_cap)).sum() \
                      if "Sales" in breach.columns else 0.0
        sim_profit  = cur_profit + recovered

        # ── Simulator KPIs ──
        sk1, sk2, sk3, sk4, sk5 = st.columns(5)
        sk1.markdown(kpi_card("Current Profit", (f"${cur_profit/1e3:,.1f}", "K"),
                              "From filtered sample", None, cur_profit >= 0, "blue", "💰"), unsafe_allow_html=True)
        sk2.markdown(kpi_card("Simulated Profit", (f"${sim_profit/1e3:,.1f}", "K"),
                              f"+${recovered:,.0f} recovery",
                              f"${recovered:,.0f}", recovered > 0, "green", "📈"), unsafe_allow_html=True)
        sk3.markdown(kpi_card("Discount Cap", (f"{disc_cap*100:.0f}", "%"),
                              "Policy threshold", None, True, "cyan", "🎚️"), unsafe_allow_html=True)
        sk4.markdown(kpi_card("Policy Violations", (f"{n_breach:,}", ""),
                              f"{breach_pct:.1f}% of orders",
                              None, False, "red", "🚨"), unsafe_allow_html=True)
        sk5.markdown(kpi_card("Recovery Rate", (f"{recovered/max(abs(cur_profit),1)*100:.1f}", "%"),
                              "Profit uplift potential",
                              None, recovered > 0, "violet", "⚡"), unsafe_allow_html=True)

        st.markdown("")

        # ── Main scatter ──
        st.markdown('<div class="section-title">🎯 Discount Rate vs Order Profit</div>', unsafe_allow_html=True)
        fig_s = go.Figure()
        # Compliant orders
        compliant = filtered[filtered["Order Item Discount Rate"] <= disc_cap]
        fig_s.add_trace(go.Scatter(
            x=compliant["Order Item Discount Rate"],
            y=compliant["Order Profit Per Order"],
            mode="markers",
            marker={"color": PALETTE["blue"], "opacity": 0.3, "size": 4},
            name="Compliant Orders"
        ))
        # Violations
        if not breach.empty:
            fig_s.add_trace(go.Scatter(
                x=breach["Order Item Discount Rate"],
                y=breach["Order Profit Per Order"],
                mode="markers",
                marker={"color": PALETTE["red"], "opacity": 0.7, "size": 5, "symbol": "x"},
                name="Policy Violation"
            ))
        fig_s.add_vline(x=disc_cap, line_dash="solid", line_color=PALETTE["green"],
                        line_width=2.5,
                        annotation_text=f"Cap: {disc_cap:.0%}",
                        annotation_font_color=PALETTE["green"],
                        annotation_bgcolor="rgba(16,185,129,0.15)")
        fig_s.add_hline(y=0, line_dash="dash", line_color=PALETTE["red"],
                        line_width=1.5, annotation_text="Break-Even",
                        annotation_font_color=PALETTE["red"])
        fig_s.update_layout(
            title="Discount Rate vs Order Profit — Policy Violations Highlighted",
            xaxis_title="Discount Rate",
            yaxis_title="Order Profit ($)",
            template=DARK_TEMPLATE, height=440,
            paper_bgcolor="#0D1426", plot_bgcolor="#0D1426",
            legend={"orientation": "h", "y": -0.15}
        )
        st.plotly_chart(fig_s, use_container_width=True)

        # ── Sensitivity Table ──
        st.markdown('<div class="section-title">📐 Sensitivity Analysis — Margin Recovery by Cap</div>', unsafe_allow_html=True)
        scenarios = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40]
        rows = []
        for cap in scenarios:
            b = filtered[filtered["Order Item Discount Rate"] > cap]
            rec = (b["Sales"] * (b["Order Item Discount Rate"] - cap)).sum() \
                  if "Sales" in b.columns else 0.0
            pct_b = len(b) / max(len(filtered), 1) * 100
            rows.append({
                "Cap":                       f"{cap:.0%}",
                "Breaching Orders":          f"{len(b):,}",
                "% Orders Affected":         f"{pct_b:.1f}%",
                "Estimated Recovery ($)":    f"${rec:,.0f}",
                "Current Policy":            "✅ Selected" if abs(cap - disc_cap) < 0.005 else ""
            })
        sens_df = pd.DataFrame(rows)
        st.dataframe(sens_df, hide_index=True, use_container_width=True)

        # ── Profit by Discount Bucket ──
        st.markdown('<div class="section-title">📊 Profit by Discount Bracket</div>', unsafe_allow_html=True)
        if "Order Item Discount Rate" in filtered.columns:
            f2 = filtered.copy()
            f2["Discount_Bucket"] = pd.cut(
                f2["Order Item Discount Rate"],
                bins=[-0.01, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.50, 1.0],
                labels=["0–5%","5–10%","10–15%","15–20%","20–25%","25–30%","30–50%","50%+"]
            )
            bucket_agg = f2.groupby("Discount_Bucket", observed=True).agg(
                Orders=("Order Profit Per Order","count"),
                Total_Profit=("Order Profit Per Order","sum"),
                Avg_Profit=("Order Profit Per Order","mean")
            ).reset_index()
            bucket_agg = bucket_agg.dropna()

            fig_b = go.Figure()
            fig_b.add_trace(go.Bar(
                x=bucket_agg["Discount_Bucket"],
                y=bucket_agg["Total_Profit"],
                name="Total Profit",
                marker_color=[PALETTE["green"] if v >= 0 else PALETTE["red"]
                              for v in bucket_agg["Total_Profit"]],
                text=[f"${v:,.0f}" for v in bucket_agg["Total_Profit"]],
                textposition="outside"
            ))
            fig_b.update_layout(
                title="Total Profit by Discount Bracket",
                xaxis_title="Discount Rate Range",
                yaxis_title="Total Profit ($)",
                template=DARK_TEMPLATE, height=380,
                paper_bgcolor="#0D1426", plot_bgcolor="#0D1426"
            )
            st.plotly_chart(fig_b, use_container_width=True)

        if recovered > 0:
            st.markdown(f"""
            <div class="alert-success">
            ✅ <b>Simulated Outcome:</b> By enforcing a <b>{disc_cap:.0%}</b> discount cap,
            APL Logistics could recover an estimated <b>${recovered:,.0f}</b> in margin
            from <b>{n_breach:,}</b> non-compliant orders ({breach_pct:.1f}% of current view).
            This represents a <b>{recovered/max(abs(cur_profit),1)*100:.1f}%</b> profit uplift.
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="alert-info">
            ℹ️ At the current <b>{disc_cap:.0%}</b> cap, no orders in the filtered view exceed the threshold.
            Try lowering the cap in the sidebar to identify potential violations.
            </div>""", unsafe_allow_html=True)

    else:
        st.markdown("""
        <div class="alert-warning">
        ⚠️ Discount analysis columns not found in the current filtered sample.
        Clear your segment/category/market filters to use the full dataset.
        </div>""", unsafe_allow_html=True)


# ── Footer ──
st.markdown("""
<hr style="border-color:#1E2D4A; margin-top:40px">
<div style="text-align:center; color:#374151; font-size:0.7rem; padding:12px 0;">
APL Logistics | Intelligence Command Center · Built with Streamlit & Plotly ·
Data refreshes on each pipeline run
</div>
""", unsafe_allow_html=True)








# import streamlit as st
# import pandas as pd
# import numpy as np
# import plotly.express as px
# import plotly.graph_objects as go
# import json
# from pathlib import Path

# # =====================================================================
# # 1. Page Configuration & Setup
# # =====================================================================
# st.set_page_config(
#     page_title="APL Logistics | Executive Command Center",
#     page_icon="📦",
#     layout="wide",
#     initial_sidebar_state="expanded"
# )

# # Custom CSS for Executive UI
# st.markdown("""
#     <style>
#     .metric-card {
#         background-color: #f8f9fa;
#         border-radius: 10px;
#         padding: 15px;
#         box-shadow: 0 4px 6px rgba(0,0,0,0.1);
#     }
#     .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
#         font-size: 1.1rem;
#         font-weight: 600;
#     }
#     </style>
# """, unsafe_allow_html=True)

# # =====================================================================
# # 2. High-Performance Data Loading (Cached)
# # =====================================================================
# @st.cache_data(show_spinner="Loading Enterprise Data...")
# def load_data():
#     """Loads JSON KPIs and Snappy-compressed Parquet files instantly."""
#     data_dir = Path("processed_data")
#     agg_dir = data_dir / "aggregations"

#     # Load KPIs
#     try:
#         with open(data_dir / 'macro_kpis.json', 'r') as f:
#             kpis = json.load(f)
#     except Exception:
#         kpis = {"total_revenue_usd": 0, "total_profit_usd": 0, "profit_margin_pct": 0, "discount_impact_ratio_pct": 0}

#     # Load Aggregations (with fallback empty DataFrames if missing)
#     def load_pq(path):
#         return pd.read_parquet(path) if path.exists() else pd.DataFrame()

#     df_cust = load_pq(agg_dir / 'customer_agg.parquet')
#     df_cat = load_pq(agg_dir / 'category_agg.parquet')
#     df_market = load_pq(agg_dir / 'market_agg.parquet')
#     df_product = load_pq(agg_dir / 'product_agg.parquet')

#     # Load UI Sample (Base data for scatter plots and cross-filtering)
#     df_base = load_pq(data_dir / 'ui_sample.parquet')
#     if df_base.empty and (data_dir / 'step1_cleaned_data.parquet').exists():
#         # Fallback to a sample of the cleaned data if ui_sample is missing
#         df_base = pd.read_parquet(data_dir / 'step1_cleaned_data.parquet').sample(n=15000, random_state=42)

#     return kpis, df_cust, df_cat, df_market, df_product, df_base

# kpis, df_cust, df_cat, df_market, df_product, df_base = load_data()

# # =====================================================================
# # 3. Dynamic Sidebar & Cross-Filtering
# # =====================================================================
# with st.sidebar:
#     st.image("https://cdn-icons-png.flaticon.com/512/2763/2763130.png", width=60)
#     st.title("Control Panel")
#     st.markdown("---")

#     # Safely extract unique values for filters
#     def get_uniques(df, col):
#         return sorted(df[col].dropna().unique().tolist()) if col in df.columns else []

#     # Filters
#     selected_segments = st.multiselect("👥 Customer Segment", options=get_uniques(df_base, 'Customer Segment'))
#     selected_categories = st.multiselect("🛍️ Category", options=get_uniques(df_base, 'Category Name'))
#     selected_markets = st.multiselect("🌍 Market", options=get_uniques(df_base, 'Market'))

#     st.markdown("---")
#     st.subheader("Pricing Controls")
#     max_discount = st.slider("📉 Max Allowed Discount Rate", min_value=0.0, max_value=0.5, value=0.25, step=0.01, format="%.2f")

# # Apply Filters to the base dataset
# filtered_base = df_base.copy()
# if selected_segments and 'Customer Segment' in filtered_base.columns:
#     filtered_base = filtered_base[filtered_base['Customer Segment'].isin(selected_segments)]
# if selected_categories and 'Category Name' in filtered_base.columns:
#     filtered_base = filtered_base[filtered_base['Category Name'].isin(selected_categories)]
# if selected_markets and 'Market' in filtered_base.columns:
#     filtered_base = filtered_base[filtered_base['Market'].isin(selected_markets)]

# # =====================================================================
# # 4. Main Dashboard Layout (Tabs)
# # =====================================================================
# st.title("APL Logistics Supply Chain Intelligence")
# st.markdown("Monitor high-level financials, detect spatial profit leaks, and simulate pricing strategies.")

# tab1, tab2, tab3, tab4 = st.tabs([
#     "📈 1. Revenue & Executive Summary",
#     "👥 2. Customer Analytics",
#     "📦 3. Product & Category",
#     "🛠️ 4. What-If Discount Simulator"
# ])

# # ---------------------------------------------------------------------
# # TAB 1: Revenue Dashboard
# # ---------------------------------------------------------------------
# with tab1:
#     st.subheader("Global Financial Overview")

#     # KPI Metric Cards
#     col1, col2, col3, col4 = st.columns(4)
#     with col1:
#         st.metric("Gross Revenue", f"${kpis.get('total_revenue_usd', 0):,.0f}")
#     with col2:
#         st.metric("Net Profit", f"${kpis.get('total_profit_usd', 0):,.0f}")
#     with col3:
#         st.metric("Profit Margin", f"{kpis.get('profit_margin_pct', 0):.2f}%")
#     with col4:
#         st.metric("Discount Leak Ratio", f"{kpis.get('discount_impact_ratio_pct', 0):.2f}%", delta="-Action Required", delta_color="inverse")

#     st.markdown("---")

#     col_a, col_b = st.columns(2)
#     with col_a:
#         if not df_market.empty:
#             fig_market = px.bar(
#                 df_market.sort_values('Total_Sales', ascending=False),
#                 x='Market', y='Total_Sales', color='Total_Profit',
#                 color_continuous_scale="Viridis",
#                 title="Revenue & Profit by Global Market"
#             )
#             st.plotly_chart(fig_market, use_container_width=True)

#     with col_b:
#         if 'Order Profit Per Order' in filtered_base.columns and 'Order Item Discount Rate' in filtered_base.columns:
#             fig_hist = px.histogram(
#                 filtered_base, x='Order Profit Per Order', nbins=50,
#                 title="Distribution of Order Profitability",
#                 color_discrete_sequence=['#2E86C1']
#             )
#             fig_hist.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Break Even")
#             st.plotly_chart(fig_hist, use_container_width=True)

# # ---------------------------------------------------------------------
# # TAB 2: Customer Dashboard
# # ---------------------------------------------------------------------
# with tab2:
#     st.subheader("Customer Segmentation & Value Mapping")
#     if not df_cust.empty:
#         col1, col2 = st.columns([2, 1])

#         with col1:
#             # Segment Distribution
#             fig_cust_scatter = px.scatter(
#                 df_cust, x='Total_Sales', y='Total_Profit',
#                 color='Customer_Value_Index' if 'Customer_Value_Index' in df_cust.columns else None,
#                 size='Order_Count', hover_name='Customer Id',
#                 color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
#                 title="Customer Matrix (Size = Order Volume, Color = Value Index)"
#             )
#             fig_cust_scatter.add_hline(y=0, line_dash="dash", line_color="black")
#             st.plotly_chart(fig_cust_scatter, use_container_width=True)

#         with col2:
#             st.info("""
#             **How to read this matrix:**
#             * **Top Right:** VIPs. High volume, high margin.
#             * **Bottom Right:** Bleeders. High volume, but costing the company money.
#             * **Top Left:** Steady standard customers.
#             * **Bottom Left:** Low value drains.
#             """)

#             top_vips = df_cust.sort_values('Total_Profit', ascending=False).head(5)
#             st.dataframe(top_vips[['Customer Id', 'Total_Sales', 'Total_Profit']], use_container_width=True, hide_index=True)

# # ---------------------------------------------------------------------
# # TAB 3: Product Dashboard
# # ---------------------------------------------------------------------
# with tab3:
#     st.subheader("Product & Category Diagnostics")
#     col1, col2 = st.columns(2)

#     with col1:
#         if not df_cat.empty:
#             top_cats = df_cat.groupby('Category Name', observed=True)['Total_Profit'].sum().reset_index().sort_values('Total_Profit', ascending=False).head(10)
#             fig_cats = px.bar(
#                 top_cats, y='Category Name', x='Total_Profit', orientation='h',
#                 title="Top 10 Categories by Pure Profit",
#                 color='Total_Profit', color_continuous_scale="Blues"
#             )
#             fig_cats.update_layout(yaxis={'categoryorder':'total ascending'})
#             st.plotly_chart(fig_cats, use_container_width=True)

#     with col2:
#         if not df_product.empty:
#             loss_products = df_product[df_product['Total_Profit'] < 0].sort_values('Total_Profit').head(10)
#             if not loss_products.empty:
#                 fig_loss = px.bar(
#                     loss_products, y='Product Name', x='Total_Profit', orientation='h',
#                     title=" Top 10 Worst Performing Products (Loss Leaders)",
#                     color_discrete_sequence=['#E74C3C']
#                 )
#                 fig_loss.update_layout(yaxis={'categoryorder':'total descending'})
#                 st.plotly_chart(fig_loss, use_container_width=True)
#             else:
#                 st.success("No purely loss-making products found at the aggregate level.")

# # ---------------------------------------------------------------------
# # TAB 4: What-If Discount Simulator
# # ---------------------------------------------------------------------
# with tab4:
#     st.subheader("What-If Pricing Strategy Simulator")
#     st.markdown(f"**Current Simulator Setting:** Cap all discounts at a maximum of **{max_discount*100:.1f}%**")

#     if 'Order Item Discount Rate' in filtered_base.columns and 'Order Profit Per Order' in filtered_base.columns:

#         # Calculate Current State
#         current_profit = filtered_base['Order Profit Per Order'].sum()

#         # Calculate Simulated State (If discounts > max were capped at max)
#         # Assuming linear relationship: new_profit = old_profit + (old_discount_amt - simulated_discount_amt)
#         # For simplicity in UI, we calculate rough recovered margin:
#         breach_mask = filtered_base['Order Item Discount Rate'] > max_discount
#         breached_orders = filtered_base[breach_mask]

#         # Rough estimation of recovered profit (Sales * (Current Discount Rate - Max Discount Rate))
#         recovered_profit = (breached_orders['Sales'] * (breached_orders['Order Item Discount Rate'] - max_discount)).sum()
#         simulated_profit = current_profit + recovered_profit

#         col1, col2, col3 = st.columns(3)
#         col1.metric("Current Sub-Sample Profit", f"${current_profit:,.0f}")
#         col2.metric("Simulated Profit", f"${simulated_profit:,.0f}", f"+${recovered_profit:,.0f} Recovered")
#         col3.metric("Orders Impacted", f"{len(breached_orders):,}", f"{(len(breached_orders)/len(filtered_base))*100:.1f}% of total")

#         st.markdown("---")

#         # Visualizing the threshold
#         fig_sim = px.scatter(
#             filtered_base, x='Order Item Discount Rate', y='Order Profit Per Order',
#             opacity=0.4, color_discrete_sequence=['#95A5A6'],
#             title="Profit Leakage Threshold Analysis"
#         )

#         # Highlight orders that violate the new policy
#         fig_sim.add_trace(go.Scatter(
#             x=breached_orders['Order Item Discount Rate'],
#             y=breached_orders['Order Profit Per Order'],
#             mode='markers', marker=dict(color='red', opacity=0.6),
#             name="Policy Violations"
#         ))

#         fig_sim.add_vline(x=max_discount, line_dash="solid", line_color="green", line_width=3, annotation_text="Proposed Hard Cap")
#         fig_sim.add_hline(y=0, line_dash="dash", line_color="black")

#         st.plotly_chart(fig_sim, use_container_width=True)
#     else:
#         st.warning("Required discount columns missing from UI sample dataset.")
