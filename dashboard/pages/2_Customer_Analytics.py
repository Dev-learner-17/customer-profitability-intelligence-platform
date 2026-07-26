import os
import sys

import plotly.express as px
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.duckdb_layer import db

st.set_page_config(page_title="Customer Analytics", page_icon="👥", layout="wide")

st.title("👥 Customer & Segmentation Analytics")
st.markdown("Powered by **DuckDB**")

try:
    df = db.query("SELECT * FROM customer_agg ORDER BY Total_Sales DESC")
except Exception:
    st.error("Error loading customer data.")
    st.stop()

st.subheader("Customer Value Distribution")
fig = px.scatter(
    df,
    x="Total_Sales",
    y="Total_Profit",
    color="Segment",
    size="Order_Count",
    hover_name="Customer ID",
    template="plotly_dark",
    title="Sales vs Profit by Customer Segment",
)
st.plotly_chart(fig, use_container_width=True)

st.subheader("Top Customers (LTV)")
top_n = st.slider("Select Top N", 10, 100, 20)
st.dataframe(df.head(top_n), use_container_width=True)
