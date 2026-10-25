from __future__ import annotations

import json
from pathlib import Path

import lightgbm as lgb
import pandas as pd
from sklearn.metrics import average_precision_score, precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import train_test_split


DATA_PATH = Path("data/fraud_orders.csv")
MODEL_PATH = Path("artifacts/lightgbm_fraud_model.txt")
METRICS_PATH = Path("artifacts/metrics.json")
FEATURES = [
    "ticket_count",
    "amount",
    "purchase_attempts_10m",
    "account_age_days",
    "device_accounts_24h",
    "payment_declines_24h",
    "hour",
    "prior_confirmed_orders",
]
THRESHOLD = 0.15


def rule_baseline(frame: pd.DataFrame) -> pd.Series:
    return (
        (frame["purchase_attempts_10m"] >= 5)
        | (frame["ticket_count"] >= 6)
        | (frame["account_age_days"] <= 2)
        | (frame["device_accounts_24h"] >= 3)
    ).astype(int)


def classification_metrics(y_true, probabilities, threshold: float) -> dict[str, float]:
    predicted = (probabilities >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, predicted, average="binary", zero_division=0
    )
    return {
        "roc_auc": round(float(roc_auc_score(y_true, probabilities)), 4),
        "pr_auc": round(float(average_precision_score(y_true, probabilities)), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "review_rate": round(float(predicted.mean()), 4),
    }


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError("Dataset missing. Run: python generate_dataset.py")
    df = pd.read_csv(DATA_PATH)
    train, test = train_test_split(
        df, test_size=0.25, random_state=20261018, stratify=df["is_fraud"]
    )
    model = lgb.LGBMClassifier(
        objective="binary",
        n_estimators=160,
        learning_rate=0.05,
        num_leaves=15,
        max_depth=5,
        min_child_samples=24,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        random_state=20261018,
        n_jobs=1,
        verbosity=-1,
    )
    model.fit(train[FEATURES], train["is_fraud"])
    test_probability = model.predict_proba(test[FEATURES])[:, 1]
    baseline_probability = rule_baseline(test).astype(float)
    metrics = {
        "dataset_rows": int(len(df)),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "fraud_rate": round(float(df["is_fraud"].mean()), 4),
        "threshold": THRESHOLD,
        "baseline_rules": classification_metrics(test["is_fraud"], baseline_probability, 0.5),
        "lightgbm": classification_metrics(test["is_fraud"], test_probability, THRESHOLD),
        "feature_importance": {
            feature: int(value)
            for feature, value in zip(FEATURES, model.feature_importances_, strict=True)
        },
    }
    MODEL_PATH.parent.mkdir(exist_ok=True)
    model.booster_.save_model(str(MODEL_PATH))
    METRICS_PATH.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
