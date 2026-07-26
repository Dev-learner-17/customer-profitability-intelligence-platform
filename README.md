# Customer & Profitability Intelligence Platform 

![License](https://img.shields.io/badge/license-MIT-blue)
![Python](https://img.shields.io/badge/python-3.10%2B-brightgreen)
![Docker](https://img.shields.io/badge/docker-ready-blue)

A production-grade, highly optimized Streamlit dashboard and ML pipeline that transforms raw supply chain transactions into actionable, executive-level business intelligence.

## 📈 Business Impact
* **Business Problem:** Identifying profit-destroying customers, over-discounted products, and high-risk delivery regions in a massive supply chain dataset.
* **Decisions Enabled:** Margin-based product retirement, algorithmic customer segmentation, dynamic discount thresholds.
* **Commercial Value:** Empowers executives to halt margin erosion and pinpoint exactly where supply chain costs outweigh revenues.

## 🏗️ Architecture
The platform is built on a modern, decoupled data engineering stack:
* **Storage Layer:** Compressed Parquet files.
* **Analytics Engine:** In-memory **DuckDB** for lightning-fast SQL aggregations without Pandas memory bloat.
* **ML Layer:** Stratified K-Fold XGBoost pipelines tuned via Optuna with MLflow tracking.
* **Presentation:** Modular Multi-page Streamlit Dashboard.

## 🚀 Quickstart
### Using Docker (Recommended)
```bash
docker-compose up --build
```
Navigate to `http://localhost:8501`

### Local Development
```bash
python -m pip install -r requirements-lock.txt
streamlit run dashboard/Home.py
```

## 📁 Repository Structure
See `PROJECT_OVERVIEW.md` and `docs/` for deep technical documentation.
