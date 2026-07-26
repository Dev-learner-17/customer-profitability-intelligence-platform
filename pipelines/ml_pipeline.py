"""
step6_ml_v2.py — APL Logistics Production ML Pipeline v2
==========================================================
Models:
  1. Delivery Risk Classifier  (order-level)
     Target  : Late_delivery_risk == 1
     Features: Shipping Mode, Product Price, Category, Market, Discount, Qty
     Expected: AUC 0.75–0.90  (shipping mode is a very strong signal)

  2. Customer LTV / Loyalty Classifier (customer-level)
     Target  : High_Value_Customer (Total Sales > 75th percentile)
     Features: Average Discount, Order Count, Market, Customer Segment, Region
     Expected: AUC 0.70–0.85 (Genuine behavioral/demographic signal, NO leakage)

Methodology:
  - Optuna TPE HPO (40 trials per model)
  - GradientBoostingClassifier (sklearn, always available)
  - Stratified 5-fold cross-validation
  - 20% OOT holdout
  - CalibratedClassifierCV (isotonic) for probability calibration
  - Permutation Feature Importance (+ SHAP if available)
  - MLflow experiment tracking (+ CSV fallback)
"""

import os
import subprocess
import sys

# ── 0. Package installer ──────────────────────────────────────────────────────
REQUIRED = {'optuna': 'optuna', 'shap': 'shap', 'mlflow': 'mlflow'}
for mod, pkg in REQUIRED.items():
    try:
        __import__(mod)
    except ImportError:
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '--quiet'])
        except Exception:
            pass

# ── 1. Imports ────────────────────────────────────────────────────────────────
import json
import logging
import random
import time
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

# Load config and set seed
try:
    with open("config.yaml", "r") as f:
        CONFIG = yaml.safe_load(f)
    SEED = CONFIG.get("project", {}).get("random_seed", 42)
except Exception:
    SEED = 42

random.seed(SEED)
np.random.seed(SEED)

warnings.filterwarnings('ignore')
os.environ['PYTHONIOENCODING'] = 'utf-8'

from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import (
    RandomizedSearchCV,
    StratifiedKFold,
    cross_val_score,
    train_test_split,
)
from sklearn.preprocessing import LabelEncoder

try:
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    OPTUNA = True
except ImportError:
    OPTUNA = False

try:
    import shap
    SHAP = True
except ImportError:
    SHAP = False

try:
    import mlflow
    import mlflow.sklearn
    os.environ.setdefault('MLFLOW_ALLOW_FILE_STORE', 'true')
    MLFLOW = True
except ImportError:
    MLFLOW = False

# ── 2. Logging ────────────────────────────────────────────────────────────────
BASE = Path("processed_data")
ML   = BASE / "ml"
ML.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | ML_v2 | %(message)s',
    handlers=[
        logging.FileHandler(BASE / "step6_ml.log", mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

log.info("=" * 60)
log.info(" APL Logistics ML Pipeline v2 - Starting")
log.info(f" Optuna={OPTUNA} | SHAP={SHAP} | MLflow={MLFLOW}")
log.info("=" * 60)

start_total = time.time()

# ── 3. MLflow Setup ───────────────────────────────────────────────────────────
if MLFLOW:
    try:
        mlflow.set_tracking_uri(str(ML / "mlruns"))
        mlflow.set_experiment("APL_Logistics_ML_v2")
    except Exception as e:
        log.warning(f"MLflow setup failed: {e}")
        MLFLOW = False

# ── 4. Data Loading ───────────────────────────────────────────────────────────
log.info("Loading datasets...")

def _safe_pq(path):
    try:
        return pd.read_parquet(path)
    except Exception as e:
        log.warning(f"Could not load {path}: {e}")
        return pd.DataFrame()

df_clean  = _safe_pq(BASE / "step1_cleaned_data.parquet")
df_cust   = _safe_pq(BASE / "aggregations" / "customer_agg.parquet")
df_rfm    = _safe_pq(BASE / "aggregations" / "rfm_segments.parquet")

log.info(f"Cleaned data: {df_clean.shape} | Customer agg: {df_cust.shape} | RFM: {df_rfm.shape}")

# ──────────────────────────────────────────────────────────────────────────────
#  MODEL 1: DELIVERY RISK (renamed from "Margin Risk" for accuracy)
#  Target : Late_delivery_risk == 1
#  Rationale: Late delivery is a direct operational risk indicator —
#  it drives expedited shipping costs, customer churn, and SLA penalties.
#  Features have genuine predictive power: Shipping Mode alone determines
#  whether Standard Class (high risk) vs Same Day (low risk) was chosen.
# ──────────────────────────────────────────────────────────────────────────────
log.info("-" * 50)
log.info("Building Delivery Risk features (order-level)...")

def build_delivery_risk_features(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    if 'Late_delivery_risk' not in df.columns:
        raise ValueError("'Late_delivery_risk' column missing from cleaned data.")

    le = LabelEncoder()
    X = pd.DataFrame(index=df.index)

    # Numerical features
    for col in ['Order Item Discount Rate', 'Order Item Quantity',
                'Order Item Product Price', 'Sales']:
        if col in df.columns:
            X[col] = df[col].astype(float)

    # Interaction features
    if 'Order Item Discount Rate' in X.columns and 'Order Item Quantity' in X.columns:
        X['disc_x_qty'] = X['Order Item Discount Rate'] * X['Order Item Quantity']
    if 'Order Item Product Price' in X.columns and 'Order Item Quantity' in X.columns:
        X['price_x_qty'] = X['Order Item Product Price'] * X['Order Item Quantity']
    if 'Order Item Product Price' in X.columns:
        X['log_price'] = np.log1p(X['Order Item Product Price'])

    # Categorical features
    for col in ['Shipping Mode', 'Market', 'Customer Segment',
                'Category Name', 'Order Status', 'Department Name']:
        if col in df.columns:
            X[col] = le.fit_transform(df[col].astype(str))

    # Target: Late delivery risk (binary: 0 = on-time, 1 = late/delayed)
    y = df['Late_delivery_risk'].astype(int)

    # Remove any NaN rows
    valid = X.notna().all(axis=1) & y.notna()
    X, y = X[valid].reset_index(drop=True), y[valid].reset_index(drop=True)
    df_valid = df[valid].reset_index(drop=True)

    pos_rate = y.mean() * 100
    log.info(f"Delivery Risk dataset: {len(X):,} rows | Late deliveries: {pos_rate:.1f}%")
    log.info(f"Features: {list(X.columns)}")
    return X, y, df_valid

try:
    X_del, y_del, df_del_src = build_delivery_risk_features(df_clean)
except Exception as e:
    log.error(f"Delivery Risk feature build failed: {e}")
    X_del, y_del, df_del_src = pd.DataFrame(), pd.Series(dtype=int), pd.DataFrame()

# ── Model 1: Optuna HPO ───────────────────────────────────────────────────────
del_report: dict[str, Any] = {}

log.info("Training Delivery Risk Model with Optuna HPO...")

if len(X_del) > 100 and len(y_del.unique()) == 2:

    X_tr, X_oot, y_tr, y_oot, idx_tr, idx_oot = train_test_split(
        X_del, y_del, X_del.index, test_size=0.20, random_state=42, stratify=y_del
    )

    cv5 = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    if OPTUNA:
        def del_objective(trial):
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 150, 600),
                'max_depth': trial.suggest_int('max_depth', 3, 8),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.25, log=True),
                'min_samples_leaf': trial.suggest_int('min_samples_leaf', 5, 50),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2', None]),
                'random_state': 42,
            }
            model = GradientBoostingClassifier(**params)
            scores = cross_val_score(model, X_tr, y_tr, cv=cv5,
                                     scoring='roc_auc', n_jobs=-1)
            return scores.mean()

        study_del = optuna.create_study(
            direction='maximize',
            sampler=optuna.samplers.TPESampler(seed=42),
            pruner=optuna.pruners.MedianPruner(n_startup_trials=5)
        )
        study_del.optimize(del_objective, n_trials=40, show_progress_bar=False)

        best_p_del = study_del.best_params
        log.info(f"Optuna best delivery AUC (CV): {study_del.best_value:.4f}")
        trials_df_del = study_del.trials_dataframe()
        trials_df_del.to_csv(ML / "optuna_margin_trials.csv", index=False)
        del_report['margin_risk_optuna_best_cv'] = round(study_del.best_value, 4)
        del_report['margin_risk_best_params']    = best_p_del
        best_model_del = GradientBoostingClassifier(**best_p_del, random_state=42)
    else:
        param_grid = {
            'n_estimators': [200, 400, 600],
            'max_depth': [3, 5, 7],
            'learning_rate': [0.05, 0.10, 0.20],
            'min_samples_leaf': [5, 15, 30],
        }
        rs = RandomizedSearchCV(GradientBoostingClassifier(random_state=42),
                                param_grid, n_iter=25, cv=cv5,
                                scoring='roc_auc', n_jobs=-1, random_state=42)
        rs.fit(X_tr, y_tr)
        best_p_del = rs.best_params_
        best_model_del = GradientBoostingClassifier(**best_p_del, random_state=42)
        del_report['margin_risk_best_params'] = best_p_del

    cv_scores_del = cross_val_score(best_model_del, X_tr, y_tr, cv=cv5,
                                    scoring='roc_auc', n_jobs=-1)
    log.info(f"Delivery Risk CV AUC: {cv_scores_del.mean():.4f} +- {cv_scores_del.std():.4f}")

    # Final fit + calibration
    final_del = CalibratedClassifierCV(best_model_del, method='isotonic', cv=3)
    final_del.fit(X_tr, y_tr)

    # OOT evaluation
    y_oot_prob_del = final_del.predict_proba(X_oot)[:, 1]
    oot_auc_del    = roc_auc_score(y_oot, y_oot_prob_del)
    brier_del      = brier_score_loss(y_oot, y_oot_prob_del)
    log.info(f"Delivery Risk OOT AUC: {oot_auc_del:.4f} | Brier: {brier_del:.4f}")

    # Feature importance
    fi_del: dict[str, float] = {}
    if SHAP:
        try:
            base_est = best_model_del
            base_est.fit(X_tr, y_tr)
            explainer = shap.TreeExplainer(base_est)
            shap_sample = X_oot.sample(min(2000, len(X_oot)), random_state=42)
            shv = explainer.shap_values(shap_sample)
            if isinstance(shv, list):
                shv = shv[1]
            mean_shap = np.abs(shv).mean(axis=0)
            fi_del = {col: float(v) for col, v in zip(X_del.columns, mean_shap)}
            fi_del = dict(sorted(fi_del.items(), key=lambda x: -x[1])[:10])
            del_report['margin_risk_shap_available'] = True
            log.info("SHAP computed for Delivery Risk model.")
        except Exception as e:
            log.warning(f"SHAP failed ({e}), using permutation importance.")

    if not fi_del:
        perm = permutation_importance(final_del, X_oot, y_oot, n_repeats=15,
                                      random_state=42, scoring='roc_auc')
        fi_del = {col: float(v) for col, v in
                  zip(X_del.columns, perm.importances_mean)}
        fi_del = dict(sorted(fi_del.items(), key=lambda x: -x[1])[:10])
        del_report['margin_risk_shap_available'] = False

    # Score all orders + save
    y_all_prob_del = final_del.predict_proba(X_del)[:, 1]
    scored_del = df_del_src.copy()
    scored_del['Margin_Risk_Probability'] = y_all_prob_del
    scored_del['Is_Loss_Order']           = y_del.values   # 1 = late delivery
    scored_del.to_parquet(ML / "margin_risk_scored_orders.parquet",
                          index=False, compression='snappy')

    del_report.update({
        'margin_risk_auc':            round(oot_auc_del, 4),
        'margin_risk_cv_mean':        round(float(cv_scores_del.mean()), 4),
        'margin_risk_cv_std':         round(float(cv_scores_del.std()), 4),
        'margin_risk_oot_auc':        round(oot_auc_del, 4),
        'margin_risk_brier_score':    round(brier_del, 4),
        'margin_risk_feature_importance': fi_del,
        'margin_risk_model_type': 'Delivery Risk Classifier (Late_delivery_risk target)',
    })

    if MLFLOW:
        try:
            with mlflow.start_run(run_name="delivery_risk_model"):
                mlflow.log_params({k: v for k, v in best_p_del.items()})
                mlflow.log_metric("cv_auc_mean", float(cv_scores_del.mean()))
                mlflow.log_metric("cv_auc_std",  float(cv_scores_del.std()))
                mlflow.log_metric("oot_auc",     oot_auc_del)
                mlflow.log_metric("brier_score", brier_del)
                mlflow.sklearn.log_model(final_del, "delivery_risk_model")
        except Exception as e:
            log.warning(f"MLflow log failed: {e}")

    log.info(f"Delivery Risk Model: CV AUC={cv_scores_del.mean():.4f} | OOT AUC={oot_auc_del:.4f}")

else:
    log.warning("Insufficient data for Delivery Risk model.")
    del_report = {
        'margin_risk_auc': 0.0, 'margin_risk_cv_mean': 0.0,
        'margin_risk_cv_std': 0.0, 'margin_risk_oot_auc': 0.0,
        'margin_risk_brier_score': 0.0, 'margin_risk_feature_importance': {},
    }


# ──────────────────────────────────────────────────────────────────────────────
#  MODEL 2: CUSTOMER LTV / LOYALTY (customer-level)
#  Target : High Value Customer (Total_Sales >= 75th percentile)
#  Rationale: Since the dataset lacks Order Dates, true future-churn prediction
#  is impossible. Predicting RFM segments from RFM features is target derivation
#  leakage (AUC=1.0). Instead, we predict which demographic/behavior profiles
#  lead to High LTV, explicitly EXCLUDING total sales/monetary features.
# ──────────────────────────────────────────────────────────────────────────────
log.info("-" * 50)
log.info("Building Customer LTV features (customer-level)...")

def build_ltv_features(
    df_clean: pd.DataFrame,
    df_cust: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:

    if df_cust.empty:
        raise ValueError("Customer agg parquet is empty.")
    
    cid_cust = next((c for c in ['Customer Id', 'Customer_Id'] if c in df_cust.columns), None)
    if not cid_cust:
        raise ValueError("No Customer ID column found in customer agg.")

    cust = df_cust.set_index(cid_cust).copy()
    
    # Target: Top 25% of customers by Total Sales
    if 'Total_Sales' not in cust.columns:
        raise ValueError("Total_Sales missing from customer agg.")
    
    q75 = cust['Total_Sales'].quantile(0.75)
    y = (cust['Total_Sales'] >= q75).astype(int)
    y.name = 'High_Value_Label'

    # Features: Exclude Total_Sales to prevent leakage!
    X = pd.DataFrame(index=cust.index)
    feat_cols = []

    # Behavioral Features
    for col in ['Average_Discount', 'Order_Count']:
        if col in cust.columns:
            X[col] = cust[col].astype(float)
            feat_cols.append(col)

    # Demographic Features from clean data (mode per customer)
    if not df_clean.empty and cid_cust in df_clean.columns:
        # Get most common segment, market, region per customer
        demo = df_clean.groupby(cid_cust)[['Customer Segment', 'Market', 'Order Region']].agg(
            lambda x: x.mode()[0] if not x.empty else 'Unknown'
        )
        le = LabelEncoder()
        for col in demo.columns:
            X[col] = le.fit_transform(demo[col].astype(str))
            feat_cols.append(col)

    X = X[feat_cols].fillna(0).replace([np.inf, -np.inf], 0)
    
    pos_rate = y.mean() * 100
    log.info(f"LTV dataset: {len(X):,} customers | High Value: {pos_rate:.1f}%")
    log.info(f"Features: {list(X.columns)}")
    return X, y

try:
    X_ltv, y_ltv = build_ltv_features(df_clean, df_cust)
except Exception as e:
    log.error(f"LTV feature build failed: {e}")
    X_ltv, y_ltv = pd.DataFrame(), pd.Series(dtype=int)

# ── Model 2: Optuna HPO ───────────────────────────────────────────────────────
ltv_report: dict[str, Any] = {}

log.info("Training Customer LTV Model with Optuna HPO...")

if len(X_ltv) > 50 and len(y_ltv.unique()) == 2:

    X_ctr, X_coot, y_ctr, y_coot = train_test_split(
        X_ltv, y_ltv, test_size=0.20, random_state=42, stratify=y_ltv
    )

    cv5c = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    if OPTUNA:
        def ltv_objective(trial):
            params = {
                'n_estimators': trial.suggest_int('n_estimators', 100, 500),
                'max_depth': trial.suggest_int('max_depth', 2, 6),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.20, log=True),
                'min_samples_leaf': trial.suggest_int('min_samples_leaf', 5, 50),
                'subsample': trial.suggest_float('subsample', 0.6, 1.0),
                'max_features': trial.suggest_categorical('max_features', ['sqrt', 'log2', None]),
                'random_state': 42,
            }
            model = GradientBoostingClassifier(**params)
            scores = cross_val_score(model, X_ctr, y_ctr, cv=cv5c,
                                     scoring='roc_auc', n_jobs=-1)
            return scores.mean()

        study_c = optuna.create_study(
            direction='maximize',
            sampler=optuna.samplers.TPESampler(seed=42),
            pruner=optuna.pruners.MedianPruner(n_startup_trials=5)
        )
        study_c.optimize(ltv_objective, n_trials=30, show_progress_bar=False)

        best_p_c = study_c.best_params
        log.info(f"Optuna best LTV AUC (CV): {study_c.best_value:.4f}")
        study_c.trials_dataframe().to_csv(ML / "optuna_ltv_trials.csv", index=False)
        ltv_report['churn_risk_optuna_best_cv'] = round(study_c.best_value, 4)
        ltv_report['churn_risk_best_params']    = best_p_c
        best_model_c = GradientBoostingClassifier(**best_p_c, random_state=42)
    else:
        param_grid_c = {
            'n_estimators': [150, 300],
            'max_depth': [3, 5],
            'learning_rate': [0.05, 0.10],
            'min_samples_leaf': [10, 25],
        }
        rs_c = RandomizedSearchCV(GradientBoostingClassifier(random_state=42),
                                  param_grid_c, n_iter=10, cv=cv5c,
                                  scoring='roc_auc', n_jobs=-1, random_state=42)
        rs_c.fit(X_ctr, y_ctr)
        best_p_c = rs_c.best_params_
        best_model_c = GradientBoostingClassifier(**best_p_c, random_state=42)
        ltv_report['churn_risk_best_params'] = best_p_c

    cv_scores_c = cross_val_score(best_model_c, X_ctr, y_ctr, cv=cv5c,
                                  scoring='roc_auc', n_jobs=-1)
    log.info(f"LTV CV AUC: {cv_scores_c.mean():.4f} +- {cv_scores_c.std():.4f}")

    final_c = CalibratedClassifierCV(best_model_c, method='isotonic', cv=3)
    final_c.fit(X_ctr, y_ctr)

    y_coot_prob = final_c.predict_proba(X_coot)[:, 1]
    oot_auc_c   = roc_auc_score(y_coot, y_coot_prob)
    brier_c     = brier_score_loss(y_coot, y_coot_prob)
    log.info(f"LTV OOT AUC: {oot_auc_c:.4f} | Brier: {brier_c:.4f}")

    # Feature importance
    fi_c: dict[str, float] = {}
    if SHAP:
        try:
            base_est_c = best_model_c
            base_est_c.fit(X_ctr, y_ctr)
            explainer_c = shap.TreeExplainer(base_est_c)
            shap_sample_c = X_coot.sample(min(1000, len(X_coot)), random_state=42)
            shv_c = explainer_c.shap_values(shap_sample_c)
            if isinstance(shv_c, list):
                shv_c = shv_c[1]
            mean_shap_c = np.abs(shv_c).mean(axis=0)
            fi_c = {col: float(v) for col, v in zip(X_ltv.columns, mean_shap_c)}
            fi_c = dict(sorted(fi_c.items(), key=lambda x: -x[1])[:10])
            log.info("SHAP computed for LTV model.")
        except Exception as e:
            log.warning(f"SHAP LTV failed: {e}")

    if not fi_c:
        perm_c = permutation_importance(final_c, X_coot, y_coot, n_repeats=15,
                                        random_state=42, scoring='roc_auc')
        fi_c = {col: float(v) for col, v in
                zip(X_ltv.columns, perm_c.importances_mean)}
        fi_c = dict(sorted(fi_c.items(), key=lambda x: -x[1])[:10])

    # Score all customers
    y_all_prob_c = final_c.predict_proba(X_ltv)[:, 1]
    scored_c = df_cust.copy()
    scored_c = scored_c.set_index(next(c for c in ['Customer Id', 'Customer_Id'] if c in df_cust.columns))
    scored_c = scored_c.loc[X_ltv.index]
    scored_c['LTV_Probability'] = y_all_prob_c
    scored_c['High_Value_Label'] = y_ltv.values
    scored_c = scored_c.reset_index()
    scored_c.to_parquet(ML / "customer_ltv_scored.parquet", index=False, compression='snappy')

    # Note: keeping dictionary keys prefixed with 'churn_' so the UI doesn't crash 
    # before we update it, but the values represent the LTV model.
    ltv_report.update({
        'churn_risk_auc':            round(oot_auc_c, 4),
        'churn_risk_cv_mean':        round(float(cv_scores_c.mean()), 4),
        'churn_risk_cv_std':         round(float(cv_scores_c.std()), 4),
        'churn_risk_oot_auc':        round(oot_auc_c, 4),
        'churn_risk_brier_score':    round(brier_c, 4),
        'churn_risk_feature_importance': fi_c,
    })

    if MLFLOW:
        try:
            with mlflow.start_run(run_name="ltv_model"):
                mlflow.log_params({k: v for k, v in best_p_c.items()})
                mlflow.log_metric("cv_auc_mean", float(cv_scores_c.mean()))
                mlflow.log_metric("cv_auc_std",  float(cv_scores_c.std()))
                mlflow.log_metric("oot_auc",     oot_auc_c)
                mlflow.log_metric("brier_score", brier_c)
                mlflow.sklearn.log_model(final_c, "ltv_model")
        except Exception as e:
            log.warning(f"MLflow LTV log failed: {e}")

    log.info(f"LTV Model: CV AUC={cv_scores_c.mean():.4f} | OOT AUC={oot_auc_c:.4f}")

else:
    log.warning("Insufficient data for LTV model.")
    ltv_report = {
        'churn_risk_auc': 0.0, 'churn_risk_cv_mean': 0.0,
        'churn_risk_cv_std': 0.0, 'churn_risk_oot_auc': 0.0,
        'churn_risk_brier_score': 0.0, 'churn_risk_feature_importance': {},
    }


# ── 5. Save model_report.json ─────────────────────────────────────────────────
full_report = {}
full_report.update(del_report)
full_report.update(ltv_report)
full_report['pipeline_version'] = 'v2'
full_report['ml_framework']     = 'GradientBoostingClassifier (sklearn)'
full_report['hpo_framework']    = 'Optuna-TPE (40 trials)' if OPTUNA else 'RandomizedSearchCV'
full_report['explainability']   = 'SHAP-TreeExplainer' if SHAP else 'PermutationImportance'
full_report['mlflow_tracked']   = MLFLOW

with open(ML / "model_report.json", 'w', encoding='utf-8') as f:
    json.dump(full_report, f, indent=4, default=str)
log.info("model_report.json updated.")

# ── 6. Summary ────────────────────────────────────────────────────────────────
elapsed = time.time() - start_total
log.info("=" * 60)
log.info(" APL Logistics ML Pipeline v2 - COMPLETE")
log.info(f" Elapsed: {elapsed:.1f}s")
log.info(f" Delivery Risk AUC (OOT): {full_report.get('margin_risk_auc', 'N/A')}")
log.info(f" Delivery Risk CV       : {full_report.get('margin_risk_cv_mean', 'N/A')} +- {full_report.get('margin_risk_cv_std', 'N/A')}")
log.info(f" Customer LTV AUC (OOT) : {full_report.get('churn_risk_auc', 'N/A')}")
log.info(f" Customer LTV CV        : {full_report.get('churn_risk_cv_mean', 'N/A')} +- {full_report.get('churn_risk_cv_std', 'N/A')}")
log.info("=" * 60)

print("\n" + "="*60)
print(f"  DELIVERY RISK -> OOT AUC: {full_report.get('margin_risk_auc', 'N/A')}"
      f"  (CV: {full_report.get('margin_risk_cv_mean', 'N/A')} +- {full_report.get('margin_risk_cv_std', 'N/A')})")
print(f"  CUSTOMER LTV  -> OOT AUC: {full_report.get('churn_risk_auc', 'N/A')}"
      f"  (CV: {full_report.get('churn_risk_cv_mean', 'N/A')} +- {full_report.get('churn_risk_cv_std', 'N/A')})")
print(f"  HPO: {full_report['hpo_framework']}")
print(f"  Explainability: {full_report['explainability']}")
print(f"  MLflow: {'Logged' if MLFLOW else 'Not available'}")
print("="*60)

