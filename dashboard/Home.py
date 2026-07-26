import os
import sys

import streamlit as st

# Ensure src is in the python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.duckdb_layer import db

st.set_page_config(
    page_title="APL Logistics | Executive Intelligence",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for a premium look
st.markdown(
    """
<style>
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: 800;
        color: #0ea5e9;
    }
    .metric-label {
        font-size: 1rem;
        color: #94a3b8;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }
</style>
""",
    unsafe_allow_html=True,
)

st.title("🚢 APL Logistics Executive Command Center")
st.markdown(
    "Welcome to the **Decision Intelligence Platform**. Select a module from the sidebar."
)

# Load Macro KPIs
kpis = db.get_macro_kpis()

if kpis:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f"""
        <div class="metric-card">
            <div class="metric-label">Gross Revenue</div>
            <div class="metric-value">${kpis.get("total_revenue_usd", 0)/1e6:,.1f}M</div>
        </div>""",
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
        <div class="metric-card">
            <div class="metric-label">Net Profit</div>
            <div class="metric-value">${kpis.get("total_profit_usd", 0)/1e6:,.1f}M</div>
        </div>""",
            unsafe_allow_html=True,
        )
    with col3:
        margin = kpis.get("profit_margin_pct", 0)
        color = "#10b981" if margin > 10 else "#f43f5e"
        st.markdown(
            f"""
        <div class="metric-card">
            <div class="metric-label">Profit Margin</div>
            <div class="metric-value" style="color: {color};">{margin:.1f}%</div>
        </div>""",
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f"""
        <div class="metric-card">
            <div class="metric-label">Total Orders</div>
            <div class="metric-value">{kpis.get("n_orders", 0):,}</div>
        </div>""",
            unsafe_allow_html=True,
        )

st.divider()

st.subheader("DuckDB Acceleration Engine")
st.info(
    "⚡ This dashboard is powered by an in-memory DuckDB analytical engine, capable of querying millions of Parquet records in milliseconds."
)

try:
    with st.spinner("Executing SQL query against Parquet..."):
        sample_df = db.query("SELECT * FROM transactions LIMIT 5")
    st.dataframe(sample_df, use_container_width=True)
except Exception as e:
    st.error(f"DuckDB Initialization Error: {e}")
