# ╔══════════════════════════════════════════════════════════════════╗
# ║  GLOBAL CONFIGURATION  (edit this block only)                   ║
# ╚══════════════════════════════════════════════════════════════════╝
from pathlib import Path

GLOBAL_CONFIG = {
    # ── Input ────────────────────────────────────────────────────────
    "raw_data_path":          "APL_Logistics.csv",

    # ── Output directories ───────────────────────────────────────────
    "output_dir":             "processed_data/",
    "agg_dir":                "processed_data/aggregations/",
    "analytics_dir":          "processed_data/analytics/",
    "plots_dir":              "processed_data/analytics/plots/",
    "spatial_dir":            "processed_data/analytics/spatial/maps/",
    "ml_dir":                 "processed_data/ml/",
    "reports_dir":            "processed_data/reports/",

    # ── Cleaning thresholds ──────────────────────────────────────────
    "financial_tolerance":    0.05,   # Allowed accounting discrepancy per row
    "zscore_threshold":       3.0,    # Std-dev cutoff for outlier removal

    # ── Analytics ────────────────────────────────────────────────────
    "pareto_target_pct":      0.80,   # 80% profit concentration threshold
    "bleeder_sales_quantile": 0.75,   # Top-quartile definition for Bleeders
    "hard_discount_cap":      0.25,   # Default recommended discount ceiling

    # ── ML ───────────────────────────────────────────────────────────
    "ml_n_estimators":        300,
    "ml_random_state":        42,
    "ml_test_size":           0.25,
    "churn_low_order_thresh": 3,      # Orders below this = potential churn

    # ── Performance ──────────────────────────────────────────────────
    "parquet_compression":    "snappy",
    "ui_sample_size":         15000,
}

# Auto-create all output directories
for key in ["output_dir","agg_dir","analytics_dir","plots_dir","spatial_dir","ml_dir","reports_dir"]:
    Path(GLOBAL_CONFIG[key]).mkdir(parents=True, exist_ok=True)

print("✅  Global config loaded. Directories created.")
print("   Directories:")
for k,v in GLOBAL_CONFIG.items():
    if "dir" in k:
        print(f"   • {v}")
# ── Production-Grade Structured Logging Setup ────────────────────────────────
import logging
import sys
from pathlib import Path


def get_logger(name: str, log_file: str | None = None) -> logging.Logger:
    """Creates a coloured, production-grade logger with optional file sink."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Stream handler
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    sh.setLevel(logging.INFO)
    logger.addHandler(sh)

    # File handler
    if log_file:
        fh = logging.FileHandler(Path(GLOBAL_CONFIG["output_dir"]) / log_file)
        fh.setFormatter(fmt)
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)

    return logger

ROOT_LOGGER = get_logger("APL", "pipeline_master.log")
ROOT_LOGGER.info("Logging system initialised.")
import json
import time
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import zscore

warnings.filterwarnings("ignore")

logger = get_logger("Step1_ETL", "step1_cleaning.log")


class APLDataCleaner:
    """
    Industrial ETL Pipeline — Step 1
    ─────────────────────────────────
    Features beyond the baseline:
      • Auto-detects every column present (no hard schema assumptions)
      • IQR fallback outlier removal if z-score is too aggressive
      • Row-level financial mismatch audit tagging
      • Cleaning report serialised to JSON for downstream auditing
      • 'Benefit per order' / 'Benefit_per_order' column normalisation
    """

    EXPECTED_DTYPES = {
        "Customer Id":              "int32",
        "Order Item Quantity":      "int16",
        "Sales":                    "float32",
        "Order Profit Per Order":   "float32",
        "Order Item Discount":      "float32",
        "Order Item Discount Rate": "float32",
        "Order Item Product Price": "float32",
        "Order Item Total":         "float32",
        "Order Item Profit Ratio":  "float32",
        "Latitude":                 "float32",
        "Longitude":                "float32",
        "Benefit per order":        "float32",
        "Late_delivery_risk":       "int8",
        "Customer Segment":         "category",
        "Market":                   "category",
        "Order Region":             "category",
        "Category Name":            "category",
        "Order Status":             "category",
        "Delivery Status":          "category",
        "Product Name":             "category",
        "Order Country":            "category",
        "Shipping Mode":            "category",
        "Department Name":          "category",
    }

    TEXT_COLS    = ["Customer City", "Customer Country", "Order City"]
    DATE_COLS    = ["order date (DateOrders)", "shipping date (DateOrders)"]
    ENCODINGS    = ["utf-8", "latin1", "ISO-8859-1", "cp1252"]

    def __init__(self, config: dict[str, Any]):
        self.config  = config
        self.df      = pd.DataFrame()
        self.report  = {}

    # ── 1.1  LOAD ──────────────────────────────────────────────────────────
    def load_data(self) -> float:
        logger.info("Analysing CSV schema …")
        try:
            header_df = pd.read_csv(self.config["raw_data_path"], nrows=1, encoding="latin1")
        except FileNotFoundError:
            logger.critical("Dataset not found: %s", self.config["raw_data_path"])
            raise

        available = header_df.columns.tolist()

        # Normalise 'Benefit per order' variant spellings
        rename_map = {}
        for col in available:
            if col.strip().lower().replace("_", " ") == "benefit per order":
                rename_map[col] = "Benefit per order"

        valid_dtypes = {k: v for k, v in self.EXPECTED_DTYPES.items() if k in available or k in rename_map.values()}
        extra_cols   = [c for c in self.TEXT_COLS + self.DATE_COLS if c in available]
        cols_to_use  = list(dict.fromkeys([k for k in valid_dtypes if k in available] + [rename_map.get(k, k) for k in valid_dtypes if k in rename_map.values()] + extra_cols))

        temp_df = None
        for enc in self.ENCODINGS:
            try:
                temp_df = pd.read_csv(self.config["raw_data_path"], usecols=lambda c: c in cols_to_use or c in rename_map, encoding=enc)
                logger.info("Loaded with encoding: %s | shape: %s", enc, temp_df.shape)
                break
            except UnicodeDecodeError:
                logger.warning("Encoding %s failed — trying next …", enc)

        if temp_df is None:
            raise ValueError("CRITICAL: All encodings exhausted. Cannot load dataset.")

        if rename_map:
            temp_df.rename(columns=rename_map, inplace=True)

        mem_before = temp_df.memory_usage(deep=True).sum() / 1e6
        final_dtypes = {k: v for k, v in valid_dtypes.items() if k in temp_df.columns}
        self.df = temp_df.astype(final_dtypes, errors="ignore")

        self.report["initial_rows"]  = len(self.df)
        self.report["initial_cols"]  = len(self.df.columns)
        self.report["mem_before_mb"] = round(mem_before, 2)
        logger.info("Shape after load: %s", self.df.shape)
        return mem_before

    # ── 1.2  CLEAN ─────────────────────────────────────────────────────────
    def clean_data(self) -> None:
        n0 = len(self.df)
        self.df.drop_duplicates(inplace=True)
        self.report["dropped_duplicates"] = n0 - len(self.df)

        n1 = len(self.df)
        critical = [c for c in ["Sales", "Order Profit Per Order", "Customer Id"] if c in self.df.columns]
        self.df.dropna(subset=critical, inplace=True)
        self.report["dropped_missing"] = n1 - len(self.df)

        for col in self.TEXT_COLS:
            if col in self.df.columns:
                self.df[col] = self.df[col].str.strip().str.upper().astype("category")

        for col in self.DATE_COLS:
            if col in self.df.columns:
                self.df[col] = pd.to_datetime(self.df[col], errors="coerce")

        logger.info("Cleaned: −%d dupes, −%d missing rows.", self.report["dropped_duplicates"], self.report["dropped_missing"])

    # ── 1.3  FINANCIAL VALIDATION ─────────────────────────────────────────
    def run_financial_validation(self) -> None:
        req = ["Order Item Product Price", "Order Item Quantity", "Order Item Discount", "Order Item Total"]
        if not all(c in self.df.columns for c in req):
            logger.warning("Skipping financial validation — required columns absent.")
            self.report["financial_mismatches"] = 0
            # NEW: tag column so downstream can filter
            self.df["_finval_ok"] = True
            return

        expected = (self.df["Order Item Product Price"] * self.df["Order Item Quantity"]) - self.df["Order Item Discount"]
        discrepancy = np.abs(self.df["Order Item Total"] - expected)

        # Tag rows before removing (audit trail)
        self.df["_finval_ok"] = discrepancy <= self.config["financial_tolerance"]

        n_bad = (~self.df["_finval_ok"]).sum()
        self.df = self.df[self.df["_finval_ok"]].copy()
        self.report["financial_mismatches"] = int(n_bad)

        if n_bad:
            logger.warning("Removed %d rows failing financial integrity check.", n_bad)
        else:
            logger.info("Financial validation passed — 0 mismatches.")

    # ── 1.4  OUTLIER REMOVAL (Z-score + IQR fallback) ─────────────────────
    def detect_outliers(self) -> None:
        numeric_cols = [c for c in ["Sales", "Order Profit Per Order", "Order Item Discount"] if c in self.df.columns]
        n0 = len(self.df)

        # Primary: Z-score
        z = np.abs(self.df[numeric_cols].apply(zscore, nan_policy="omit"))
        mask_z = (z < self.config["zscore_threshold"]).all(axis=1)

        # Fallback: if z-score removes more than 5% of rows, switch to IQR
        z_removal_pct = 1 - mask_z.mean()
        if z_removal_pct > 0.05:
            logger.warning("Z-score would remove %.1f%% of rows — switching to IQR fallback.", z_removal_pct * 100)
            q1, q3  = self.df[numeric_cols].quantile(0.25), self.df[numeric_cols].quantile(0.75)
            iqr     = q3 - q1
            lb, ub  = q1 - 3 * iqr, q3 + 3 * iqr
            mask_iqr = ((self.df[numeric_cols] >= lb) & (self.df[numeric_cols] <= ub)).all(axis=1)
            self.df  = self.df[mask_iqr].copy()
            method   = "IQR"
        else:
            self.df = self.df[mask_z].copy()
            method  = "Z-score"

        removed = n0 - len(self.df)
        self.report["outliers_removed"] = removed
        self.report["outlier_method"]   = method
        logger.info("Outlier removal (%s): removed %d rows (%.2f%%).", method, removed, removed / n0 * 100)

    # ── 1.5  REPORT & SAVE ────────────────────────────────────────────────
    def generate_report(self) -> None:
        mem_after = self.df.memory_usage(deep=True).sum() / 1e6
        self.report["final_rows"]   = len(self.df)
        self.report["mem_after_mb"] = round(mem_after, 2)
        reduction = (1 - mem_after / self.report["mem_before_mb"]) * 100

        logger.info("=" * 55)
        logger.info("  STEP 1 REPORT")
        logger.info("  Initial rows      : %s", f"{self.report['initial_rows']:,}")
        logger.info("  Final rows        : %s", f"{self.report['final_rows']:,}")
        logger.info("  Duplicates removed: %s", f"{self.report['dropped_duplicates']:,}")
        logger.info("  Missing removed   : %s", f"{self.report['dropped_missing']:,}")
        logger.info("  Financial bad rows: %s", f"{self.report['financial_mismatches']:,}")
        logger.info("  Outliers removed  : %s (%s)", f"{self.report['outliers_removed']:,}", self.report["outlier_method"])
        logger.info("  Memory reduction  : %.1f%%  (%.2fMB → %.2fMB)", reduction, self.report["mem_before_mb"], self.report["mem_after_mb"])
        logger.info("=" * 55)

        out = Path(self.config["output_dir"])
        self.df.to_parquet(out / "step1_cleaned_data.parquet", index=False, compression=self.config["parquet_compression"])
        with open(out / "step1_cleaning_report.json", "w") as f:
            json.dump(self.report, f, indent=4)
        logger.info("Cleaned data saved.")


# ── Execute Step 1 ──────────────────────────────────────────────────────────
t0 = time.time()
cleaner = APLDataCleaner(GLOBAL_CONFIG)
cleaner.load_data()
cleaner.clean_data()
cleaner.run_financial_validation()
cleaner.detect_outliers()
cleaner.generate_report()
logger.info("Step 1 complete in %.2fs", time.time() - t0)
import time
from pathlib import Path

logger = get_logger("Step2_KPI", "step2_kpi.log")


class APLKPIEngineer:
    """
    Step 2 — Advanced KPI Engineering
    ──────────────────────────────────
    New capabilities:
      • MoM revenue & profit trend detection
      • Customer Lifetime Value (CLV) estimation
      • Category Health Score
      • Segment-level discount elasticity
      • Benefit-per-order vs profit cross-validation
    """

    def __init__(self, config):
        self.config     = config
        self.df         = pd.DataFrame()
        self.macro_kpis = {}

    def load(self):
        p = Path(self.config["output_dir"]) / "step1_cleaned_data.parquet"
        self.df = pd.read_parquet(p)
        logger.info("Loaded %s rows × %s cols", *self.df.shape)

    # ── 2.1  Macro KPIs ───────────────────────────────────────────────────
    def calculate_macro_kpis(self):
        logger.info("Calculating macro KPIs …")
        rev  = float(self.df["Sales"].sum())
        prof = float(self.df["Order Profit Per Order"].sum())
        margin = prof / rev * 100 if rev else 0.0

        # Discount-free counterfactual margin
        nodis  = self.df[self.df["Order Item Discount Rate"] == 0]
        rev0   = float(nodis["Sales"].sum())
        prof0  = float(nodis["Order Profit Per Order"].sum())
        m0     = prof0 / rev0 * 100 if rev0 else 0.0
        disc_impact = round(m0 - margin, 4)

        # Benefit-per-order validation (if column exists)
        bpo_total = float(self.df["Benefit per order"].sum()) if "Benefit per order" in self.df.columns else None
        bpo_delta = round(bpo_total - prof, 2) if bpo_total is not None else None

        # Average order value
        order_col = "Order Id" if "Order Id" in self.df.columns else "Sales"
        n_orders  = self.df[order_col].nunique() if order_col == "Order Id" else len(self.df)
        aov       = rev / n_orders if n_orders else 0

        cat_margin = float(self.df.groupby("Category Name", observed=True)["Order Item Profit Ratio"].mean().mean() * 100)                      if "Category Name" in self.df.columns else 0.0

        self.macro_kpis = {
            "total_revenue_usd":            round(rev, 2),
            "total_profit_usd":             round(prof, 2),
            "profit_margin_pct":            round(margin, 4),
            "margin_zero_discount_pct":     round(m0, 4),
            "discount_impact_ratio_pct":    disc_impact,
            "average_category_margin_pct":  round(cat_margin, 4),
            "average_order_value_usd":      round(aov, 2),
            "n_unique_customers":           int(self.df["Customer Id"].nunique()),
            "n_orders":                     int(n_orders),
            "benefit_per_order_total":      bpo_total,
            "benefit_vs_profit_delta":      bpo_delta,
        }
        logger.info("Rev: $%s | Margin: %.2f%% | Discount leak: %.2f%%", f"{rev:,.0f}", margin, disc_impact)

    # ── 2.2  Monthly Revenue & Profit Trend ───────────────────────────────
    def calculate_monthly_trend(self):
        date_col = next((c for c in ["order date (DateOrders)", "Order Date"] if c in self.df.columns), None)
        if date_col is None:
            logger.warning("No date column found — skipping MoM trend.")
            return

        self.df["_month"] = pd.to_datetime(self.df[date_col], errors="coerce").dt.to_period("M")
        trend = self.df.groupby("_month", observed=True).agg(
            Monthly_Revenue=("Sales", "sum"),
            Monthly_Profit=("Order Profit Per Order", "sum"),
            Order_Count=("Sales", "count"),
        ).reset_index()
        trend["_month"] = trend["_month"].astype(str)
        trend["MoM_Revenue_Growth_pct"] = trend["Monthly_Revenue"].pct_change() * 100
        trend["MoM_Profit_Growth_pct"]  = trend["Monthly_Profit"].pct_change() * 100

        out = Path(self.config["output_dir"]) / "monthly_trend.parquet"
        trend.to_parquet(out, index=False, compression=self.config["parquet_compression"])
        logger.info("Monthly trend saved (%d months).", len(trend))

    # ── 2.3  Customer Lifetime Value (CLV) ────────────────────────────────
    def calculate_clv(self):
        logger.info("Estimating Customer Lifetime Value (CLV) …")
        order_col = "Order Id" if "Order Id" in self.df.columns else "Sales"
        agg_func  = "nunique" if order_col == "Order Id" else "count"

        clv = self.df.groupby("Customer Id", observed=True).agg(
            Total_Revenue=("Sales", "sum"),
            Total_Profit=("Order Profit Per Order", "sum"),
            Order_Count=(order_col, agg_func),
            Avg_Discount=("Order Item Discount Rate", "mean"),
        ).reset_index()

        # CLV estimate: total profit × (1 + ln(order_count))  — logarithmic loyalty factor
        clv["CLV_Score"] = clv["Total_Profit"] * (1 + np.log1p(clv["Order_Count"]))
        clv["CLV_Score"] = clv["CLV_Score"].astype("float32")

        # Churn risk flag: customers with very few orders
        clv["Churn_Risk"] = clv["Order_Count"] <= self.config["churn_low_order_thresh"]

        out = Path(self.config["output_dir"]) / "customer_clv.parquet"
        clv.to_parquet(out, index=False, compression=self.config["parquet_compression"])
        logger.info("CLV engineered for %d customers. High-churn-risk: %d.", len(clv), clv["Churn_Risk"].sum())

    # ── 2.4  Category Health Score ────────────────────────────────────────
    def calculate_category_health(self):
        if "Category Name" not in self.df.columns:
            return
        logger.info("Computing Category Health Scores …")
        ch = self.df.groupby("Category Name", observed=True).agg(
            Total_Revenue=("Sales", "sum"),
            Total_Profit=("Order Profit Per Order", "sum"),
            Avg_Profit_Ratio=("Order Item Profit Ratio", "mean"),
            Volume=("Sales", "count"),
        ).reset_index()

        # Normalise (0–1 min-max) then blend: 60% margin-focus, 40% volume-focus
        def norm(s): return (s - s.min()) / (s.max() - s.min() + 1e-9)
        ch["Health_Score"] = 0.6 * norm(ch["Avg_Profit_Ratio"]) + 0.4 * norm(ch["Volume"])
        ch["Health_Score"] = ch["Health_Score"].round(4)

        out = Path(self.config["agg_dir"]) / "category_health.parquet"
        ch.to_parquet(out, index=False, compression=self.config["parquet_compression"])
        logger.info("Category health scores saved.")

    # ── 2.5  Segment Discount Elasticity ─────────────────────────────────
    def calculate_discount_elasticity(self):
        if not all(c in self.df.columns for c in ["Customer Segment", "Order Item Discount Rate", "Order Profit Per Order"]):
            return
        logger.info("Calculating segment discount elasticity …")
        # Pearson correlation of discount_rate vs profit per segment
        elas = self.df.groupby("Customer Segment", observed=True).apply(
            lambda g: g[["Order Item Discount Rate", "Order Profit Per Order"]].corr().iloc[0, 1]
        ).reset_index()
        elas.columns = ["Customer Segment", "Discount_Profit_Correlation"]
        self.macro_kpis["segment_discount_elasticity"] = elas.set_index("Customer Segment")["Discount_Profit_Correlation"].to_dict()
        logger.info("Elasticity: %s", elas.to_dict("records"))

    # ── 2.6  Export ──────────────────────────────────────────────────────
    def export(self):
        out = Path(self.config["output_dir"]) / "macro_kpis.json"
        with open(out, "w") as f:
            json.dump(self.macro_kpis, f, indent=4, default=str)
        logger.info("KPIs exported to %s", out)


# ── Execute Step 2 ──────────────────────────────────────────────────────────
t0 = time.time()
kpi_eng = APLKPIEngineer(GLOBAL_CONFIG)
kpi_eng.load()
kpi_eng.calculate_macro_kpis()
kpi_eng.calculate_monthly_trend()
kpi_eng.calculate_clv()
kpi_eng.calculate_category_health()
kpi_eng.calculate_discount_elasticity()
kpi_eng.export()
logger.info("Step 2 complete in %.2fs", time.time() - t0)
import time
from pathlib import Path

logger = get_logger("Step3_FE", "step3_features.log")


class APLFeatureEngineer:
    """
    Step 3 — Feature Engineering & Pre-Aggregation
    ─────────────────────────────────────────────────
    Produces Snappy-compressed Parquet slices optimised for
    sub-100ms Streamlit chart rendering.
    """

    def __init__(self, config):
        self.config = config
        self.df     = pd.DataFrame()

    def load(self):
        self.df = pd.read_parquet(Path(self.config["output_dir"]) / "step1_cleaned_data.parquet")
        logger.info("Loaded %d rows.", len(self.df))

    # ── Utility ───────────────────────────────────────────────────────────
    def _save(self, df_out: pd.DataFrame, filename: str):
        for col in df_out.select_dtypes("float64").columns:
            df_out[col] = df_out[col].astype("float32")
        p = Path(self.config["agg_dir"]) / filename
        df_out.to_parquet(p, index=False, compression=self.config["parquet_compression"])
        logger.info("Saved %s — %d rows.", filename, len(df_out))

    # ── 3.1  Engineer Row-Level Features ─────────────────────────────────
    def engineer_row_features(self):
        # Delivery delay
        order_col    = next((c for c in ["order date (DateOrders)", "Order Date"] if c in self.df.columns), None)
        ship_col     = next((c for c in ["shipping date (DateOrders)", "Ship Date"] if c in self.df.columns), None)
        sched_col    = "Days for shipment (scheduled)" if "Days for shipment (scheduled)" in self.df.columns else None

        if order_col and ship_col:
            self.df["_order_dt"] = pd.to_datetime(self.df[order_col], errors="coerce")
            self.df["_ship_dt"]  = pd.to_datetime(self.df[ship_col],  errors="coerce")
            self.df["Delivery_Delay_Days"] = (self.df["_ship_dt"] - self.df["_order_dt"]).dt.days
            if sched_col:
                self.df["Delivery_Overrun_Days"] = self.df["Delivery_Delay_Days"] - self.df[sched_col]
        elif "Days for shipping (real)" in self.df.columns and sched_col:
            self.df["Delivery_Overrun_Days"] = self.df["Days for shipping (real)"] - self.df[sched_col]

        # Margin band
        if "Order Item Profit Ratio" in self.df.columns:
            bins   = [-np.inf, 0, 0.10, 0.25, np.inf]
            labels = ["Loss", "Thin (<10%)", "Healthy (10-25%)", "Star (>25%)"]
            self.df["Margin_Band"] = pd.cut(self.df["Order Item Profit Ratio"], bins=bins, labels=labels)

        logger.info("Row-level features engineered.")

    # ── 3.2  Customer Aggregation ─────────────────────────────────────────
    def aggregate_customers(self):
        order_col = "Order Id" if "Order Id" in self.df.columns else "Sales"
        agg_func  = "nunique" if order_col == "Order Id" else "count"

        df_c = self.df.groupby("Customer Id", observed=True).agg(
            Total_Sales        =("Sales", "sum"),
            Total_Profit       =("Order Profit Per Order", "sum"),
            Avg_Discount       =("Order Item Discount Rate", "mean"),
            Order_Count        =(order_col, agg_func),
            Avg_Profit_Ratio   =("Order Item Profit Ratio", "mean"),
        ).reset_index()

        df_c["Customer_Value_Index"] = np.where(
            df_c["Order_Count"] > 0, df_c["Total_Profit"] / df_c["Order_Count"], 0.0
        ).astype("float32")

        # Add segment if available
        if "Customer Segment" in self.df.columns:
            seg_map = self.df.groupby("Customer Id", observed=True)["Customer Segment"].agg(lambda x: x.mode()[0]).reset_index()
            df_c    = df_c.merge(seg_map, on="Customer Id", how="left")

        self._save(df_c, "customer_agg.parquet")

    # ── 3.3  Category Aggregation ─────────────────────────────────────────
    def aggregate_categories(self):
        df_cat = self.df.groupby("Category Name", observed=True).agg(
            Total_Sales       =("Sales", "sum"),
            Total_Profit      =("Order Profit Per Order", "sum"),
            Avg_Profit_Ratio  =("Order Item Profit Ratio", "mean"),
            Units_Sold        =("Order Item Quantity", "sum"),
        ).reset_index()
        # Herfindahl concentration index
        total_rev = df_cat["Total_Sales"].sum()
        df_cat["Revenue_Share"] = df_cat["Total_Sales"] / total_rev
        df_cat["HHI_Contribution"] = df_cat["Revenue_Share"] ** 2
        self._save(df_cat, "category_agg.parquet")

    # ── 3.4  Product Aggregation ──────────────────────────────────────────
    def aggregate_products(self):
        df_p = self.df.groupby("Product Name", observed=True).agg(
            Total_Sales   =("Sales", "sum"),
            Total_Profit  =("Order Profit Per Order", "sum"),
            Units_Sold    =("Order Item Quantity", "sum"),
            Avg_Discount  =("Order Item Discount Rate", "mean"),
        ).reset_index()
        df_p["Profit_Per_Unit"] = np.where(df_p["Units_Sold"] > 0, df_p["Total_Profit"] / df_p["Units_Sold"], 0)
        self._save(df_p, "product_agg.parquet")

    # ── 3.5  Market & Region Aggregations ────────────────────────────────
    def aggregate_market_and_region(self):
        for grp_col, fname in [("Market", "market_agg.parquet"), ("Order Region", "region_agg.parquet")]:
            if grp_col not in self.df.columns:
                continue
            df_m = self.df.groupby(grp_col, observed=True).agg(
                Total_Sales   =("Sales", "sum"),
                Total_Profit  =("Order Profit Per Order", "sum"),
                Order_Count   =("Sales", "count"),
            ).reset_index()
            df_m["Profit_Margin_pct"] = df_m["Total_Profit"] / df_m["Total_Sales"] * 100
            self._save(df_m, fname)

    # ── 3.6  Shipping Mode Aggregation ───────────────────────────────────
    def aggregate_shipping(self):
        if "Shipping Mode" not in self.df.columns:
            return
        cols = ["Shipping Mode"]
        agg  = {"Total_Sales": ("Sales", "sum"), "Total_Profit": ("Order Profit Per Order", "sum"), "Order_Count": ("Sales", "count")}
        if "Delivery_Overrun_Days" in self.df.columns:
            agg["Avg_Overrun_Days"] = ("Delivery_Overrun_Days", "mean")
        df_s = self.df.groupby(cols, observed=True).agg(**agg).reset_index()
        self._save(df_s, "shipping_agg.parquet")

    # ── 3.7  UI Sample ────────────────────────────────────────────────────
    def create_ui_sample(self):
        keep = [c for c in [
            "Order Item Discount Rate", "Order Profit Per Order", "Sales",
            "Customer Segment", "Category Name", "Product Name", "Market",
            "Order Item Profit Ratio", "Margin_Band", "Shipping Mode",
            "Order Item Quantity", "Late_delivery_risk",
        ] if c in self.df.columns]
        sample = self.df[keep].sample(n=min(self.config["ui_sample_size"], len(self.df)), random_state=42)
        p = Path(self.config["output_dir"]) / "ui_sample.parquet"
        sample.to_parquet(p, index=False, compression=self.config["parquet_compression"])
        logger.info("UI sample saved (%d rows).", len(sample))


# ── Execute Step 3 ──────────────────────────────────────────────────────────
t0 = time.time()
fe = APLFeatureEngineer(GLOBAL_CONFIG)
fe.load()
fe.engineer_row_features()
fe.aggregate_customers()
fe.aggregate_categories()
fe.aggregate_products()
fe.aggregate_market_and_region()
fe.aggregate_shipping()
fe.create_ui_sample()
logger.info("Step 3 complete in %.2fs", time.time() - t0)
import time
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

logger = get_logger("Step4_Analytics", "step4_analytics.log")


class APLAdvancedAnalytics:
    """
    Step 4 — Advanced Analytics
    ─────────────────────────────
    Modules:
      1. Pareto (80/20) customer profit concentration
      2. RFM segmentation
      3. Cohort retention (if dates available)
      4. ABC inventory classification
      5. Discount threshold & revenue-at-risk
      6. Customer segmentation matrix
      7. Correlation heatmap
      8. Shipping mode profitability
    """

    def __init__(self, config):
        self.config   = config
        self.df       = pd.DataFrame()
        self.df_cust  = pd.DataFrame()
        self.insights = {}

    def load(self):
        self.df      = pd.read_parquet(Path(self.config["output_dir"]) / "step1_cleaned_data.parquet")
        self.df_cust = pd.read_parquet(Path(self.config["agg_dir"])    / "customer_agg.parquet")
        logger.info("Loaded base: %s | customer: %s", self.df.shape, self.df_cust.shape)

    def _savefig(self, fig, name: str):
        p = Path(self.config["plots_dir"]) / name
        fig.write_html(str(p))
        logger.info("Plot saved: %s", p)

    # ── 4.1  Pareto Analysis ─────────────────────────────────────────────
    def pareto_analysis(self):
        logger.info("Running Pareto (80/20) analysis …")
        pos = self.df_cust[self.df_cust["Total_Profit"] > 0].sort_values("Total_Profit", ascending=False).copy()
        pos["Cumulative_Profit"]   = pos["Total_Profit"].cumsum()
        pos["Cumulative_Pct"]      = pos["Cumulative_Profit"] / pos["Total_Profit"].sum()
        threshold_idx              = (pos["Cumulative_Pct"] <= self.config["pareto_target_pct"]).sum()
        pareto_pct                 = threshold_idx / len(self.df_cust) * 100
        self.insights["pareto_pct"]= round(pareto_pct, 2)
        logger.info("PARETO: %.2f%% of customers drive 80%% of positive profit.", pareto_pct)

        fig = go.Figure()
        fig.add_bar(x=np.arange(len(pos)), y=pos["Total_Profit"], name="Profit", marker_color="#1E3A5F")
        total_p = pos["Total_Profit"].sum()
        fig.add_scatter(x=np.arange(len(pos)), y=pos["Cumulative_Pct"] * total_p,
                        name="Cumulative %", mode="lines", yaxis="y2",
                        line={"color": "#F4A261", "width": 3})
        fig.add_vline(x=threshold_idx, line_dash="dash", line_color="red",
                      annotation_text=f"Top {pareto_pct:.1f}%")
        fig.update_layout(title=f"Customer Profit Pareto — {pareto_pct:.1f}% drive 80% of profit",
                          xaxis_title="Customers (ranked)", yaxis_title="Profit ($)",
                          yaxis2={"overlaying": "y", "side": "right", "title": "Cumulative Profit"},
                          template="plotly_white")
        self._savefig(fig, "pareto_chart.html")

    # ── 4.2  RFM Segmentation ────────────────────────────────────────────
    def rfm_segmentation(self):
        logger.info("Running RFM segmentation …")
        date_col = next((c for c in ["order date (DateOrders)", "Order Date"] if c in self.df.columns), None)

        if date_col:
            self.df["_date"] = pd.to_datetime(self.df[date_col], errors="coerce")
            snapshot         = self.df["_date"].max()
            order_col        = "Order Id" if "Order Id" in self.df.columns else "Sales"
            agg_func         = "nunique" if order_col == "Order Id" else "count"

            rfm = self.df.groupby("Customer Id", observed=True).agg(
                Recency    =("_date",   lambda x: (snapshot - x.max()).days),
                Frequency  =(order_col, agg_func),
                Monetary   =("Sales",   "sum"),
            ).reset_index()
        else:
            # No dates — use order count as frequency proxy
            rfm = self.df_cust[["Customer Id", "Total_Sales", "Order_Count"]].copy()
            rfm.columns = ["Customer Id", "Monetary", "Frequency"]
            rfm["Recency"] = np.nan

        # Score 1-4 (qcut) each dimension
        for col, asc in [("Recency", True), ("Frequency", False), ("Monetary", False)]:
            if col in rfm.columns and rfm[col].notna().any():
                try:
                    rfm[f"{col}_Score"] = pd.qcut(rfm[col], q=4, labels=[4,3,2,1] if asc else [1,2,3,4], duplicates="drop")
                except Exception:
                    rfm[f"{col}_Score"] = 2  # fallback

        score_cols = [c for c in ["Recency_Score","Frequency_Score","Monetary_Score"] if c in rfm.columns]
        rfm["RFM_Total"] = rfm[score_cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)

        def label(score):
            if score >= 10: return "Champions"
            if score >= 8:  return "Loyal"
            if score >= 6:  return "Potential Loyalist"
            if score >= 4:  return "At Risk"
            return          "Lost"

        rfm["RFM_Segment"] = rfm["RFM_Total"].apply(label)

        out = Path(self.config["agg_dir"]) / "rfm_segments.parquet"
        rfm.to_parquet(out, index=False, compression=self.config["parquet_compression"])
        seg_dist = rfm["RFM_Segment"].value_counts().to_dict()
        self.insights["rfm_distribution"] = seg_dist
        logger.info("RFM segments: %s", seg_dist)

        fig = px.bar(rfm["RFM_Segment"].value_counts().reset_index(),
                     x="RFM_Segment", y="count",
                     color="RFM_Segment", title="RFM Customer Segment Distribution",
                     template="plotly_white")
        self._savefig(fig, "rfm_segments.html")

    # ── 4.3  ABC Inventory Classification ───────────────────────────────
    def abc_classification(self):
        logger.info("Running ABC inventory classification …")
        df_prod = pd.read_parquet(Path(self.config["agg_dir"]) / "product_agg.parquet")
        df_prod = df_prod.sort_values("Total_Profit", ascending=False)
        df_prod["Cumulative_Profit_Pct"] = df_prod["Total_Profit"].cumsum() / df_prod["Total_Profit"].sum()

        df_prod["ABC_Class"] = np.select(
            [df_prod["Cumulative_Profit_Pct"] <= 0.70,
             df_prod["Cumulative_Profit_Pct"] <= 0.90],
            ["A (Top 70%)", "B (70–90%)"],
            default="C (Bottom 10%)"
        )

        out = Path(self.config["agg_dir"]) / "abc_classification.parquet"
        df_prod.to_parquet(out, index=False, compression=self.config["parquet_compression"])
        counts = df_prod["ABC_Class"].value_counts().to_dict()
        logger.info("ABC: %s", counts)

        fig = px.bar(df_prod.head(20), y="Product Name", x="Total_Profit", orientation="h",
                     color="ABC_Class", title="Top 20 Products — ABC Profit Classification",
                     template="plotly_white")
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        self._savefig(fig, "abc_classification.html")

    # ── 4.4  Discount Threshold & Revenue-at-Risk ────────────────────────
    def discount_and_revenue_at_risk(self):
        logger.info("Computing discount threshold and revenue-at-risk …")
        self.df["Discount_Bracket"] = pd.cut(self.df["Order Item Discount Rate"], bins=np.arange(0, 1.05, 0.05))
        curve = self.df.groupby("Discount_Bracket", observed=True)["Order Profit Per Order"].mean().reset_index()
        curve["Bracket_Str"] = curve["Discount_Bracket"].astype(str)

        breach = self.df[self.df["Order Item Discount Rate"] > self.config["hard_discount_cap"]]
        rar    = float((breach["Sales"] * (breach["Order Item Discount Rate"] - self.config["hard_discount_cap"])).sum())
        self.insights["revenue_at_risk_usd"] = round(rar, 2)
        logger.info("Revenue-at-Risk from discount overrides: $%s", f"{rar:,.0f}")

        fig = px.line(curve, x="Bracket_Str", y="Order Profit Per Order", markers=True,
                      title="Average Order Profit by Discount Bracket",
                      labels={"Bracket_Str": "Discount Bracket", "Order Profit Per Order": "Avg Profit ($)"},
                      template="plotly_white")
        fig.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="Break-Even")
        fig.add_vline(x=str(pd.cut([self.config["hard_discount_cap"]], bins=np.arange(0,1.05,0.05))[0]),
                      line_dash="dot", line_color="green", annotation_text="Recommended Cap")
        self._savefig(fig, "discount_threshold.html")

    # ── 4.5  Customer Segmentation Matrix ────────────────────────────────
    def customer_segmentation(self):
        logger.info("Executing behavioural customer segmentation …")
        s75 = self.df_cust["Total_Sales"].quantile(self.config["bleeder_sales_quantile"])
        conditions = [
            (self.df_cust["Total_Sales"] >= s75) & (self.df_cust["Total_Profit"] > 0),
            (self.df_cust["Total_Sales"] >= s75) & (self.df_cust["Total_Profit"] <= 0),
            (self.df_cust["Total_Sales"] <  s75) & (self.df_cust["Total_Profit"] <= 0),
        ]
        choices = ["VIP (High Value)", "Bleeder (High Vol, Loss)", "Low Value (Drain)"]
        self.df_cust["Segment_Class"] = np.select(conditions, choices, default="Standard")

        out = Path(self.config["agg_dir"]) / "segmented_customers.parquet"
        self.df_cust.to_parquet(out, index=False, compression=self.config["parquet_compression"])
        n_bleeders = (self.df_cust["Segment_Class"] == "Bleeder (High Vol, Loss)").sum()
        self.insights["n_bleeders"] = int(n_bleeders)
        logger.info("Bleeders identified: %d", n_bleeders)

        fig = px.scatter(self.df_cust, x="Total_Sales", y="Total_Profit",
                         color="Segment_Class", title="Customer Value Matrix",
                         color_discrete_map={"VIP (High Value)":"#2ECC71","Bleeder (High Vol, Loss)":"#E74C3C","Standard":"#3498DB","Low Value (Drain)":"#95A5A6"},
                         opacity=0.55, template="plotly_white")
        fig.add_hline(y=0, line_dash="dash", line_color="black")
        fig.add_vline(x=s75, line_dash="dash", line_color="black", annotation_text="Top 25% Sales")
        self._savefig(fig, "customer_segmentation_matrix.html")

    # ── 4.6  Correlation Heatmap ─────────────────────────────────────────
    def correlation_heatmap(self):
        cols = [c for c in ["Order Item Discount Rate","Order Profit Per Order","Sales","Order Item Quantity","Order Item Profit Ratio"] if c in self.df.columns]
        corr = self.df[cols].corr(method="pearson")
        disc_profit = corr.loc["Order Item Discount Rate","Order Profit Per Order"] if "Order Item Discount Rate" in corr else None
        if disc_profit is not None:
            self.insights["discount_profit_correlation"] = round(float(disc_profit), 4)
            logger.info("Discount vs Profit correlation: %.4f", disc_profit)

        fig = px.imshow(corr.round(3), text_auto=True, color_continuous_scale="RdBu_r",
                        title="Financial Metrics Correlation Matrix", template="plotly_white")
        self._savefig(fig, "correlation_heatmap.html")

    # ── 4.7  Shipping Mode Profitability ─────────────────────────────────
    def shipping_profitability(self):
        if "Shipping Mode" not in self.df.columns:
            return
        df_s = pd.read_parquet(Path(self.config["agg_dir"]) / "shipping_agg.parquet")
        df_s["Profit_Margin_pct"] = df_s["Total_Profit"] / df_s["Total_Sales"] * 100
        fig = px.bar(df_s, x="Shipping Mode", y="Profit_Margin_pct",
                     color="Profit_Margin_pct", color_continuous_scale="RdYlGn",
                     title="Profit Margin % by Shipping Mode", template="plotly_white")
        self._savefig(fig, "shipping_profitability.html")

    # ── 4.8  Save Insights ────────────────────────────────────────────────
    def save_insights(self):
        with open(Path(self.config["analytics_dir"]) / "analytics_insights.json", "w") as f:
            json.dump(self.insights, f, indent=4, default=str)
        logger.info("Insights saved: %s", self.insights)


# ── Execute Step 4 ──────────────────────────────────────────────────────────
t0 = time.time()
ana = APLAdvancedAnalytics(GLOBAL_CONFIG)
ana.load()
ana.pareto_analysis()
ana.rfm_segmentation()
ana.abc_classification()
ana.discount_and_revenue_at_risk()
ana.customer_segmentation()
ana.correlation_heatmap()
ana.shipping_profitability()
ana.save_insights()
logger.info("Step 4 complete in %.2fs", time.time() - t0)
import time
from pathlib import Path

import folium
import pandas as pd
from folium.plugins import HeatMap, MarkerCluster

logger = get_logger("Step5_Geo", "step5_spatial.log")


class APLSpatialAnalytics:

    def __init__(self, config):
        self.config   = config
        self.df_base  = pd.DataFrame()
        self.df_geo   = pd.DataFrame()

    def load(self):
        self.df_base = pd.read_parquet(Path(self.config["output_dir"]) / "step1_cleaned_data.parquet")
        req = ["Latitude","Longitude","Order Profit Per Order","Sales"]
        if not all(c in self.df_base.columns for c in req):
            logger.error("Spatial columns missing — skipping Step 5.")
            return

        grp = ["Latitude","Longitude"]
        for c in ["Order City","Order Country"]:
            if c in self.df_base.columns: grp.append(c)

        self.df_geo = self.df_base.groupby(grp, observed=True).agg(
            Total_Profit  =("Order Profit Per Order", "sum"),
            Total_Sales   =("Sales", "sum"),
            Order_Count   =("Sales", "count"),
        ).reset_index()
        self.df_geo["Profit_Status"] = np.where(self.df_geo["Total_Profit"] >= 0, "Profitable","Loss-Making")
        out = Path(self.config["spatial_dir"]).parent / "spatial_nodes_agg.parquet"
        self.df_geo.to_parquet(out, index=False, compression=self.config["parquet_compression"])
        logger.info("Geo aggregated: %d → %d nodes.", len(self.df_base), len(self.df_geo))

    def plotly_map(self):
        if self.df_geo.empty: return
        maxp = max(abs(self.df_geo["Total_Profit"].min()), abs(self.df_geo["Total_Profit"].max()))
        hover = {"Total_Profit":":.0f","Total_Sales":":.0f","Order_Count":True,"Latitude":False,"Longitude":False}
        if "Order City" in self.df_geo.columns: hover["Order City"] = True

        fig = px.scatter_mapbox(
            self.df_geo, lat="Latitude", lon="Longitude",
            color="Total_Profit", size="Order_Count",
            color_continuous_scale=px.colors.diverging.RdYlGn,
            range_color=[-maxp, maxp], color_continuous_midpoint=0,
            hover_name="Order City" if "Order City" in self.df_geo.columns else None,
            hover_data=hover, zoom=1.5, mapbox_style="open-street-map",
            title="Global Profitability Map — bubble size = order volume"
        )
        fig.update_layout(margin={"r": 0,"t": 40,"l": 0,"b": 0})
        p = Path(self.config["spatial_dir"]) / "plotly_profit_map.html"
        fig.write_html(str(p))
        logger.info("Plotly map saved.")

    def folium_map(self):
        if self.df_geo.empty: return
        lat0, lon0 = self.df_geo["Latitude"].mean(), self.df_geo["Longitude"].mean()
        m = folium.Map(location=[lat0, lon0], zoom_start=2, tiles="CartoDB positron")

        profit_c = MarkerCluster(name="Profitable Nodes").add_to(m)
        loss_c   = MarkerCluster(name="Loss-Making Leaks").add_to(m)

        # Heatmap layer for density context
        heat_data = self.df_geo[["Latitude","Longitude","Order_Count"]].values.tolist()
        HeatMap(heat_data, name="Order Density", radius=8, blur=10).add_to(m)

        for _, r in self.df_geo.iterrows():
            color  = "green" if r["Total_Profit"] >= 0 else "red"
            target = profit_c if r["Total_Profit"] >= 0 else loss_c
            city   = r.get("Order City","Unknown")
            popup  = f"""<b>{city}</b><br>
                Sales: ${r['Total_Sales']:,.0f}<br>
                Profit: <span style='color:{color}'>${r['Total_Profit']:,.0f}</span><br>
                Orders: {r['Order_Count']}"""
            folium.CircleMarker(
                [r["Latitude"], r["Longitude"]],
                radius=min(max(r["Order_Count"]/10, 3), 15),
                popup=folium.Popup(popup, max_width=300),
                color=color, fill=True, fill_color=color, fill_opacity=0.7
            ).add_to(target)

        folium.LayerControl().add_to(m)
        p = Path(self.config["spatial_dir"]) / "folium_leak_detector.html"
        m.save(str(p))
        logger.info("Folium map saved.")


t0 = time.time()
geo = APLSpatialAnalytics(GLOBAL_CONFIG)
geo.load()
geo.plotly_map()
geo.folium_map()
logger.info("Step 5 complete in %.2fs", time.time() - t0)
import time
from pathlib import Path

import pandas as pd
import xgboost as xgb
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

logger = get_logger("Step6_ML", "step6_ml.log")


class APLRiskScorer:
    """
    Step 6 — XGBoost-based Margin & Churn Risk Scoring
    ─────────────────────────────────────────────────────
    Model 1 (Margin Risk):
      Target  : Is order profit < 0?
      Features: discount rate, quantity, product price, shipping mode, market, segment

    Model 2 (Churn Risk):
      Target  : Churn_Risk flag from CLV table
      Features: order_count, total_revenue, avg_discount, avg_profit_ratio
    """

    def __init__(self, config):
        self.config   = config
        self.df       = pd.DataFrame()
        self.df_clv   = pd.DataFrame()
        self.report   = {}

    def load(self):
        self.df     = pd.read_parquet(Path(self.config["output_dir"]) / "step1_cleaned_data.parquet")
        clv_path    = Path(self.config["output_dir"]) / "customer_clv.parquet"
        if clv_path.exists():
            self.df_clv = pd.read_parquet(clv_path)

    # ── Shared: LabelEncode categoricals ─────────────────────────────────
    @staticmethod
    def _encode(df: pd.DataFrame, cat_cols: list) -> pd.DataFrame:
        df = df.copy()
        for col in cat_cols:
            if col in df.columns:
                df[col] = LabelEncoder().fit_transform(df[col].astype(str))
        return df

    # ── 6.1  Margin Risk Model ────────────────────────────────────────────
    def train_margin_risk_model(self):
        logger.info("Training Margin Risk Classifier …")
        FEATURES = [c for c in [
            "Order Item Discount Rate", "Order Item Quantity", "Order Item Product Price",
            "Shipping Mode", "Market", "Customer Segment", "Category Name",
        ] if c in self.df.columns]

        df_m = self.df[FEATURES + ["Order Profit Per Order"]].dropna()
        df_m["Target_LossOrder"] = (df_m["Order Profit Per Order"] < 0).astype(int)

        cat_cols = [c for c in ["Shipping Mode","Market","Customer Segment","Category Name"] if c in df_m.columns]
        df_enc   = self._encode(df_m[FEATURES], cat_cols)

        X = df_enc.values
        y = df_m["Target_LossOrder"].values

        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=self.config["ml_test_size"],
                                                    random_state=self.config["ml_random_state"],
                                                    stratify=y)

        model = xgb.XGBClassifier(
            n_estimators      = self.config["ml_n_estimators"],
            max_depth         = 6,
            learning_rate     = 0.05,
            subsample         = 0.8,
            colsample_bytree  = 0.8,
            use_label_encoder = False,
            eval_metric       = "logloss",
            random_state      = self.config["ml_random_state"],
        )
        model.fit(X_tr, y_tr, eval_set=[(X_te, y_te)], verbose=False)

        y_prob = model.predict_proba(X_te)[:, 1]
        auc    = roc_auc_score(y_te, y_prob)
        logger.info("Margin Risk Model AUC: %.4f", auc)
        self.report["margin_risk_auc"] = round(auc, 4)

        # Score full dataset
        df_full_enc   = self._encode(self.df[FEATURES].fillna(0), cat_cols)
        risk_prob     = model.predict_proba(df_full_enc.values)[:, 1]
        df_scored     = self.df[["Customer Id"] + FEATURES + ["Order Profit Per Order"]].copy()
        df_scored["Margin_Risk_Probability"] = risk_prob.astype("float32")
        df_scored["Margin_Risk_Flag"]        = (risk_prob > 0.5).astype("int8")

        feat_imp = dict(zip(FEATURES, model.feature_importances_.tolist()))
        self.report["margin_risk_feature_importance"] = feat_imp

        out = Path(self.config["ml_dir"]) / "margin_risk_scored_orders.parquet"
        df_scored.to_parquet(out, index=False, compression=self.config["parquet_compression"])
        logger.info("Margin risk scores saved.")

    # ── 6.2  Churn Risk Model ─────────────────────────────────────────────
    def train_churn_risk_model(self):
        if self.df_clv.empty or "Churn_Risk" not in self.df_clv.columns:
            logger.warning("CLV data missing — skipping churn model.")
            return

        logger.info("Training Customer Churn Risk Model …")
        FEATURES = [c for c in ["Total_Revenue","Total_Profit","Order_Count","Avg_Discount","CLV_Score"] if c in self.df_clv.columns]
        df_c = self.df_clv[FEATURES + ["Churn_Risk","Customer Id"]].dropna()

        X = df_c[FEATURES].values
        y = df_c["Churn_Risk"].astype(int).values

        if y.sum() < 10:
            logger.warning("Insufficient churn positives — skipping.")
            return

        X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=self.config["ml_test_size"],
                                                    random_state=self.config["ml_random_state"], stratify=y)

        model = xgb.XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.1,
                                   use_label_encoder=False, eval_metric="logloss",
                                   random_state=self.config["ml_random_state"])
        model.fit(X_tr, y_tr, verbose=False)
        auc = roc_auc_score(y_te, model.predict_proba(X_te)[:,1])
        logger.info("Churn Risk Model AUC: %.4f", auc)
        self.report["churn_risk_auc"] = round(auc, 4)

        df_c["Churn_Probability"] = model.predict_proba(X)[:,1].astype("float32")
        out = Path(self.config["ml_dir"]) / "customer_churn_risk.parquet"
        df_c[["Customer Id","Total_Revenue","Order_Count","Churn_Probability","Churn_Risk"]].to_parquet(out, index=False, compression=self.config["parquet_compression"])
        logger.info("Churn risk scores saved.")

    def save_report(self):
        with open(Path(self.config["ml_dir"]) / "model_report.json", "w") as f:
            json.dump(self.report, f, indent=4)
        logger.info("ML model report: %s", self.report)


t0 = time.time()
ml = APLRiskScorer(GLOBAL_CONFIG)
ml.load()
ml.train_margin_risk_model()
ml.train_churn_risk_model()
ml.save_report()
logger.info("Step 6 complete in %.2fs", time.time() - t0)
