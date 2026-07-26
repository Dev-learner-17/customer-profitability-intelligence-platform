import os
import sys

import plotly.express as px
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.duckdb_layer import db

st.set_page_config(page_title="ML Risk Engine", page_icon="🤖", layout="wide")

st.title("🤖 Machine Learning Risk Engine")

try:
    df_margin = db.query("SELECT * FROM margin_risk_scored_orders LIMIT 1000")
    df_ltv = db.query("SELECT * FROM customer_churn_risk LIMIT 1000")
except Exception:
    st.error("ML inferences not found. Have you run ml_pipeline.py?")
    st.stop()

col1, col2 = st.columns(2)
with col1:
    st.subheader("Delivery Risk Inference")
    fig1 = px.histogram(df_margin, x="Margin_Risk_Prob", template="plotly_dark", title="Delivery Risk Distribution")
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("Customer LTV Inference")
    fig2 = px.histogram(df_ltv, x="LTV_Prob", template="plotly_dark", title="High LTV Probability Distribution")
    st.plotly_chart(fig2, use_container_width=True)
