import json
from pathlib import Path

import duckdb
import pandas as pd


class DuckDBLayer:
    """
    High-performance data access layer using DuckDB.
    Replaces pd.read_parquet for large-scale dashboard filtering.
    """
    def __init__(self, data_dir: str = "processed_data"):
        self.data_dir = Path(data_dir)
        self.conn = duckdb.connect(database=':memory:', read_only=False)
        self._register_views()

    def _register_views(self):
        """Registers Parquet files as DuckDB views for instant querying."""
        # Main transactions
        main_pq = self.data_dir / "step1_cleaned_data.parquet"
        if main_pq.exists():
            self.conn.execute(f"CREATE OR REPLACE VIEW transactions AS SELECT * FROM read_parquet('{main_pq}')")
        
        # Aggregations
        agg_dir = self.data_dir / "aggregations"
        if agg_dir.exists():
            for pq_file in agg_dir.glob("*.parquet"):
                view_name = pq_file.stem
                self.conn.execute(f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM read_parquet('{pq_file}')")
        
        # ML scoring
        ml_dir = self.data_dir / "ml"
        if ml_dir.exists():
            for pq_file in ml_dir.glob("*.parquet"):
                view_name = pq_file.stem
                self.conn.execute(f"CREATE OR REPLACE VIEW {view_name} AS SELECT * FROM read_parquet('{pq_file}')")

    def query(self, sql: str) -> pd.DataFrame:
        """Execute SQL and return Pandas DataFrame."""
        return self.conn.execute(sql).df()

    def get_macro_kpis(self) -> dict:
        """Loads pre-calculated macro KPIs."""
        kpi_path = self.data_dir / "macro_kpis.json"
        if kpi_path.exists():
            with open(kpi_path, 'r') as f:
                return json.load(f)
        return {}

    def get_customer_summary(self, limit: int = 100) -> pd.DataFrame:
        """Example: Quick pull from DuckDB."""
        return self.query(f"SELECT * FROM customer_agg ORDER BY Total_Sales DESC LIMIT {limit}")

    def close(self):
        self.conn.close()

import streamlit as st


@st.cache_resource
def get_duckdb_connection():
    return DuckDBLayer()

# Singleton instance for the dashboard
db = get_duckdb_connection()
db = DuckDBLayer()
