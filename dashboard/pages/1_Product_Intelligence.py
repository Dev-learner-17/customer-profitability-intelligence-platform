import os
import sys

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.duckdb_layer import db

st.set_page_config(page_title="Product Intelligence", page_icon="📦", layout="wide")

st.title("📦 Product Intelligence Matrix")
st.markdown("Powered by **DuckDB** and **Product Efficiency Index (PEI)**")

# Fetch advanced product features
try:
    df = db.query("SELECT * FROM product_agg_advanced WHERE Total_Sales > 1000")
except Exception:
    st.error(
        "Error loading advanced product data. Have you run feature_engineering.py?"
    )
    st.stop()

# ---------------------------------------------------------
# 1. Profitability Quadrant Analysis (BCG Matrix style)
# ---------------------------------------------------------
st.subheader("Profitability Quadrant Analysis")
st.markdown(
    "Identifies high-volume vs high-margin products to guide strategic investment."
)

# Calculate medians for quadrant split
median_vol = df["Units_Sold"].median()
median_margin = df["Margin"].median()


def assign_quadrant(row):
    if row["Units_Sold"] >= median_vol and row["Margin"] >= median_margin:
        return "Stars (High Vol, High Margin)"
    elif row["Units_Sold"] < median_vol and row["Margin"] >= median_margin:
        return "Niche (Low Vol, High Margin)"
    elif row["Units_Sold"] >= median_vol and row["Margin"] < median_margin:
        return "Cash Cows (High Vol, Low Margin)"
    else:
        return "Dogs (Low Vol, Low Margin)"


df["Quadrant"] = df.apply(assign_quadrant, axis=1)

fig_quad = px.scatter(
    df,
    x="Units_Sold",
    y="Margin",
    color="Quadrant",
    size="Total_Sales",
    hover_name="Product Name",
    color_discrete_map={
        "Stars (High Vol, High Margin)": "#10b981",
        "Niche (Low Vol, High Margin)": "#3b82f6",
        "Cash Cows (High Vol, Low Margin)": "#f59e0b",
        "Dogs (Low Vol, Low Margin)": "#ef4444",
    },
    template="plotly_dark",
    labels={"Units_Sold": "Sales Volume (Units)", "Margin": "Profit Margin (%)"},
)

fig_quad.add_hline(
    y=median_margin,
    line_dash="dash",
    line_color="gray",
    annotation_text="Median Margin",
)
fig_quad.add_vline(
    x=median_vol, line_dash="dash", line_color="gray", annotation_text="Median Volume"
)
fig_quad.update_layout(height=600)
st.plotly_chart(fig_quad, use_container_width=True)


# ---------------------------------------------------------
# 2. Top Products by Product Efficiency Index (PEI)
# ---------------------------------------------------------
st.subheader("Top Products by Efficiency Index (PEI)")
st.markdown(
    "PEI balances Margin (40%), Profit Density (30%), and Volume Contribution (30%)."
)

top_pei = df.sort_values(by="Product_Efficiency_Index", ascending=False).head(10)

fig_pei = px.bar(
    top_pei,
    x="Product_Efficiency_Index",
    y="Product Name",
    orientation="h",
    color="Margin",
    color_continuous_scale="Viridis",
    template="plotly_dark",
    title="Highest Efficiency Products",
)
fig_pei.update_layout(yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig_pei, use_container_width=True)

# ---------------------------------------------------------
# 3. Discount Sensitivity Curves
# ---------------------------------------------------------
st.subheader("Discount Sensitivity Curves")
st.markdown(
    "SQL aggregation over millions of rows via DuckDB to find the optimal discount threshold."
)

# Query transactions directly to get volume at different discount brackets
disc_query = """
SELECT 
    ROUND("Order Item Discount Rate" * 20) / 20 AS Discount_Bracket,
    COUNT(*) AS Order_Count,
    SUM("Order Item Profit Ratio") / COUNT(*) AS Avg_Margin,
    SUM(Sales) AS Total_Revenue
FROM transactions
WHERE "Order Item Discount Rate" <= 0.30
GROUP BY 1
ORDER BY 1
"""
disc_df = db.query(disc_query)

fig_disc = go.Figure()
fig_disc.add_trace(
    go.Bar(
        x=disc_df["Discount_Bracket"],
        y=disc_df["Order_Count"],
        name="Order Volume",
        marker_color="#3b82f6",
        yaxis="y1",
    )
)
fig_disc.add_trace(
    go.Scatter(
        x=disc_df["Discount_Bracket"],
        y=disc_df["Avg_Margin"],
        name="Avg Margin",
        line={"color": "#f43f5e", "width": 3},
        yaxis="y2",
    )
)

fig_disc.update_layout(
    template="plotly_dark",
    title="Volume vs Margin by Discount Depth",
    yaxis={"title": "Order Volume", "side": "left"},
    yaxis2={
        "title": "Average Margin",
        "side": "right",
        "overlaying": "y",
        "tickformat": ".0%",
    },
    xaxis={"title": "Discount Rate", "tickformat": ".0%"},
    height=500,
)
st.plotly_chart(fig_disc, use_container_width=True)
