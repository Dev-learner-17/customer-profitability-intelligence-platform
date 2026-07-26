# Customer & Profitability Intelligence Platform

## The Business Problem
Supply chains operate on thin margins. APL Logistics required a comprehensive intelligence platform to identify which customers, products, and markets were destroying value through over-discounting or high fulfillment costs. The original data existed in siloed, monolithic formats lacking real-time analytical capabilities.

## The Solution
We engineered a full-stack Customer & Profitability Intelligence Platform that ingests raw supply chain data, validates financial metrics, engineers advanced KPIs (Product Efficiency Index, Customer Lifetime Value), and serves them through a high-performance in-memory analytical engine (DuckDB). 

## Architecture
- **Data Engineering:** Class-based Python ETL pipelines with strict financial validation schemas.
- **Machine Learning:** Two specialized models (Delivery Risk and Customer Loyalty) tuned via Optuna with SHAP explainability.
- **Analytics Engine:** DuckDB layer transforming 175,000+ rows into millisecond aggregates.
- **Presentation:** A modular Streamlit dashboard architecture.

## Decisions Enabled
- **Discount Thresholding:** Identifying exactly where discounts begin to cannibalize profit margins.
- **Customer Segmentation:** Automatically tiering customers based on LTV and profitability.
- **Product Portfolio Optimization:** Identifying 'Dog' products (low volume, low margin) for retirement.
