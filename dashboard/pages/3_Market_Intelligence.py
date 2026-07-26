import os
import sys

import plotly.express as px
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.duckdb_layer import db

st.set_page_config(page_title="Market Intelligence", page_icon="🌍", layout="wide")

st.title("🌍 Market & Regional Intelligence")

try:
    df = db.query("SELECT * FROM market_agg")
except Exception:
    st.error("Error loading market data.")
    st.stop()

st.subheader("Global Profitability")
fig = px.treemap(
    df, path=["Market"], values="Total_Sales", color="Total_Profit",
    color_continuous_scale="RdYlGn", template="plotly_dark",
    title="Market Revenue (Size) & Profit (Color)"
)
st.plotly_chart(fig, use_container_width=True)

st.dataframe(df.sort_values(by="Total_Profit", ascending=False), use_container_width=True)
