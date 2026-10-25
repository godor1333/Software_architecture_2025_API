import os
import json
import joblib
import numpy as np
import pandas as pd
from xgboost import XGBClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
    classification_report
)

def generate_synthetic_clickstream_dataset(n_samples: int = 15000, random_state: int = 42):
    np.random.seed(random_state)
    records = []

    for i in range(n_samples):
        # 15% фрод-трафика
        is_fraud = 1 if np.random.rand() < 0.15 else 0

        if is_fraud:
            fraud_type = np.random.choice(["botnet", "click_farm", "fast_clicker", "stealth_bot"])
            if fraud_type == "botnet":
                clicks_1min = np.random.randint(15, 60)
                clicks_5min = clicks_1min * np.random.randint(3, 6)
                interval = np.random.uniform(30, 250)
                ua_bot = np.random.choice([0.0, 1.0], p=[0.35, 0.65])
                is_dc = np.random.choice([0.0, 1.0], p=[0.2, 0.8])
                device_mismatch = np.random.choice([0.0, 1.0], p=[0.75, 0.25])
            elif fraud_type == "click_farm":
                clicks_1min = np.random.randint(4, 18)
                clicks_5min = clicks_1min * np.random.randint(3, 5)
                interval = np.random.uniform(400, 1500)
                ua_bot = 0.0
                is_dc = np.random.choice([0.0, 1.0], p=[0.55, 0.45])
                device_mismatch = np.random.choice([0.0, 1.0], p=[0.85, 0.15])
            elif fraud_type == "stealth_bot":
                # Маскируется под человека
                clicks_1min = np.random.choice([1, 2, 3, 5], p=[0.5, 0.3, 0.15, 0.05])
                clicks_5min = clicks_1min + np.random.randint(1, 4)
                interval = np.random.uniform(600, 3000)
                ua_bot = 0.0
                is_dc = np.random.choice([0.0, 1.0], p=[0.5, 0.5])
                device_mismatch = np.random.choice([0.0, 1.0], p=[0.9, 0.1])
            else:  # fast_clicker
                clicks_1min = np.random.randint(10, 40)
                clicks_5min = clicks_1min * 2
                interval = np.random.uniform(20, 180)
                ua_bot = np.random.choice([0.0, 1.0], p=[0.5, 0.5])
                is_dc = np.random.choice([0.0, 1.0], p=[0.5, 0.5])
                device_mismatch = 0.0
            hour = np.random.randint(0, 24)
        else:
            # Легитимный пользователь (с естественным шумом)
            clicks_1min = np.random.choice([1, 2, 3, 5, 8], p=[0.78, 0.14, 0.05, 0.02, 0.01])
            clicks_5min = clicks_1min + np.random.randint(0, 6)
            # Случайные дабл-клики или быстрые нажатия
            if np.random.rand() < 0.05:
                interval = np.random.uniform(80, 250)
            else:
                interval = np.random.exponential(scale=2800) + 350
            ua_bot = 0.0
            is_dc = np.random.choice([0.0, 1.0], p=[0.92, 0.08])
            device_mismatch = np.random.choice([0.0, 1.0], p=[0.96, 0.04])
            hour = np.random.choice(range(24), p=[
                0.01, 0.01, 0.01, 0.01, 0.02, 0.03,
                0.04, 0.05, 0.06, 0.07, 0.07, 0.07,
                0.07, 0.07, 0.07, 0.06, 0.06, 0.06,
                0.05, 0.04, 0.03, 0.02, 0.01, 0.01
            ])

        fast_click_flag = 1.0 if interval < 250.0 else 0.0
        night_hours = 1.0 if 1 <= hour <= 5 else 0.0

        records.append({
            "clicks_1min": float(clicks_1min),
            "clicks_5min": float(clicks_5min),
            "click_interval_ms": float(interval),
            "fast_click_flag": float(fast_click_flag),
            "ua_bot_score": float(ua_bot),
            "is_datacenter_ip": float(is_dc),
            "device_mismatch": float(device_mismatch),
            "night_hours": float(night_hours),
            "hour": float(hour),
            "is_fraud": is_fraud
        })

    return pd.DataFrame(records)

def train_and_evaluate():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    df = generate_synthetic_clickstream_dataset(n_samples=20000, random_state=42)

    feature_cols = [
        "clicks_1min",
        "clicks_5min",
        "click_interval_ms",
        "fast_click_flag",
        "ua_bot_score",
        "is_datacenter_ip",
        "device_mismatch",
        "night_hours",
        "hour"
    ]

    X = df[feature_cols]
    y = df["is_fraud"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    # 1. Baseline: Logistic Regression
    baseline_clf = LogisticRegression(max_iter=1000, random_state=42)
    baseline_clf.fit(X_train, y_train)
    base_preds_proba = baseline_clf.predict_proba(X_test)[:, 1]
    base_preds = (base_preds_proba >= 0.5).astype(int)

    base_roc_auc = float(roc_auc_score(y_test, base_preds_proba))
    base_pr_auc = float(average_precision_score(y_test, base_preds_proba))
    base_f1 = float(f1_score(y_test, base_preds))
    base_precision = float(precision_score(y_test, base_preds))
    base_recall = float(recall_score(y_test, base_preds))

    # 2. Main Model: XGBoost
    xgb_clf = XGBClassifier(
        n_estimators=120,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        scale_pos_weight=2.5,
        eval_metric="logloss",
        random_state=42
    )

    xgb_clf.fit(X_train, y_train)

    xgb_preds_proba = xgb_clf.predict_proba(X_test)[:, 1]
    xgb_preds = (xgb_preds_proba >= 0.5).astype(int)

    xgb_roc_auc = float(roc_auc_score(y_test, xgb_preds_proba))
    xgb_pr_auc = float(average_precision_score(y_test, xgb_preds_proba))
    xgb_f1 = float(f1_score(y_test, xgb_preds))
    xgb_precision = float(precision_score(y_test, xgb_preds))
    xgb_recall = float(recall_score(y_test, xgb_preds))
    cm = confusion_matrix(y_test, xgb_preds).tolist()

    feature_importances = {
        col: float(imp) for col, imp in zip(feature_cols, xgb_clf.feature_importances_)
    }

    # Сохраняем модель
    model_path = os.path.join(current_dir, "model.joblib")
    joblib.dump(xgb_clf, model_path)

    metrics = {
        "dataset_size": len(df),
        "train_size": len(X_train),
        "test_size": len(X_test),
        "fraud_ratio": float(y.mean()),
        "feature_names": feature_cols,
        "feature_importances": feature_importances,
        "baseline_logistic_regression": {
            "roc_auc": round(base_roc_auc, 4),
            "pr_auc": round(base_pr_auc, 4),
            "f1": round(base_f1, 4),
            "precision": round(base_precision, 4),
            "recall": round(base_recall, 4)
        },
        "xgboost_model": {
            "roc_auc": round(xgb_roc_auc, 4),
            "pr_auc": round(xgb_pr_auc, 4),
            "f1": round(xgb_f1, 4),
            "precision": round(xgb_precision, 4),
            "recall": round(xgb_recall, 4),
            "confusion_matrix": {
                "tn": cm[0][0],
                "fp": cm[0][1],
                "fn": cm[1][0],
                "tp": cm[1][1]
            }
        }
    }

    metrics_path = os.path.join(current_dir, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print("Model trained and evaluated successfully!")
    print(f"Baseline F1: {base_f1:.4f}, ROC-AUC: {base_roc_auc:.4f}")
    print(f"XGBoost  F1: {xgb_f1:.4f}, ROC-AUC: {xgb_roc_auc:.4f}")
    print("Metrics saved to:", metrics_path)

if __name__ == "__main__":
    train_and_evaluate()
