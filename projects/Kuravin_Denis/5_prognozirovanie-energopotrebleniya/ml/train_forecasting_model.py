import os
import json
import joblib
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from .feature_pipeline import TimeSeriesFeaturePipeline

def generate_building_telemetry_dataset(n_hours: int = 8760, random_state: int = 42) -> pd.DataFrame:
    """Генерирует часовой временной ряд телеметрии умного здания за 1 год (8 760 часов)."""
    np.random.seed(random_state)
    records = []

    # Моделируем синусоиду температуры по сезонам
    hours = np.arange(n_hours)
    # Сезонный цикл (365 дней) + суточный цикл (24 часа)
    day_of_year = (hours // 24) % 365
    hour_of_day = hours % 24
    day_of_week = (hours // 24) % 7

    season_temp = 5.0 + 15.0 * np.sin(2 * np.pi * (day_of_year - 100) / 365.0)
    daily_temp = 4.0 * np.sin(2 * np.pi * (hour_of_day - 9) / 24.0)
    outside_temp = season_temp + daily_temp + np.random.normal(0, 1.5, n_hours)
    humidity = np.clip(60.0 - 0.8 * daily_temp + np.random.normal(0, 5.0, n_hours), 20.0, 95.0)

    # Базовая нагрузка кампуса: 220 кВт
    base_load = 220.0
    # Профиль активности: пик в рабочие часы 09:00 - 18:00
    work_hour_mult = np.where((hour_of_day >= 8) & (hour_of_day <= 18), 2.4, 1.1)
    # Выходные дни (суббота, воскресенье)
    weekend_mult = np.where((day_of_week == 5) | (day_of_week == 6), 0.55, 1.0)
    # Нагрузка на климат-контроль (HVAC): растет при температуре < 10°C и > 22°C
    hvac_load = np.maximum(0.0, (16.0 - outside_temp) * 6.0) + np.maximum(0.0, (outside_temp - 21.0) * 8.5)

    power_kwh = base_load * work_hour_mult * weekend_mult + hvac_load + np.random.normal(0, 12.0, n_hours)
    power_kwh = np.maximum(150.0, power_kwh)

    df = pd.DataFrame({
        "hour": hour_of_day,
        "day_of_week": day_of_week,
        "temp_c": outside_temp,
        "humidity_pct": humidity,
        "power_kwh": power_kwh
    })

    # Создаем лаги
    df["lag_1h"] = df["power_kwh"].shift(1).bfill()
    df["lag_24h"] = df["power_kwh"].shift(24).bfill()
    df["rolling_mean_6h"] = df["power_kwh"].shift(1).rolling(window=6, min_periods=1).mean().bfill()
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(float)
    df["sin_hour"] = np.sin(2 * np.pi * df["hour"] / 24.0)
    df["cos_hour"] = np.cos(2 * np.pi * df["hour"] / 24.0)
    df["temp_effect"] = (df["temp_c"] - 18.0) ** 2

    return df

def train_and_evaluate():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    df = generate_building_telemetry_dataset(n_hours=8760, random_state=42)

    features = [
        "hour", "sin_hour", "cos_hour", "day_of_week", "is_weekend",
        "temp_c", "temp_effect", "humidity_pct",
        "lag_1h", "lag_24h", "rolling_mean_6h"
    ]

    # Разбиение по времени: первые 10 месяцев train (7 000 часов), последние 2 месяца test (1 760 часов)
    train_size = 7000
    X_train = df[features].iloc[:train_size]
    y_train = df["power_kwh"].iloc[:train_size]
    X_test = df[features].iloc[train_size:]
    y_test = df["power_kwh"].iloc[train_size:]

    # 1. Baseline: Naive Persistence (берем значение вчера в этот же час lag_24h)
    baseline_preds = X_test["lag_24h"]
    base_rmse = float(np.sqrt(mean_squared_error(y_test, baseline_preds)))
    base_mae = float(mean_absolute_error(y_test, baseline_preds))
    base_r2 = float(r2_score(y_test, baseline_preds))
    base_mape = float(np.mean(np.abs((y_test - baseline_preds) / y_test)) * 100.0)

    # 2. Main Model: XGBoost Regressor
    xgb_reg = XGBRegressor(
        n_estimators=120,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42
    )
    xgb_reg.fit(X_train, y_train)

    xgb_preds = xgb_reg.predict(X_test)
    xgb_rmse = float(np.sqrt(mean_squared_error(y_test, xgb_preds)))
    xgb_mae = float(mean_absolute_error(y_test, xgb_preds))
    xgb_r2 = float(r2_score(y_test, xgb_preds))
    xgb_mape = float(np.mean(np.abs((y_test - xgb_preds) / y_test)) * 100.0)

    # Расчет стандартного отклонения остатков ошибки для 3-Sigma детектора аномалий
    residuals = y_test - xgb_preds
    residual_std = float(np.std(residuals))
    residual_mean = float(np.mean(residuals))

    feature_importances = {
        col: round(float(imp), 4) for col, imp in zip(features, xgb_reg.feature_importances_)
    }

    # Сохраняем модель
    model_path = os.path.join(current_dir, "model.joblib")
    joblib.dump(xgb_reg, model_path)

    metrics = {
        "dataset_name": "ASHRAE Great Energy Predictor III (Smart Campus Synthetic)",
        "total_hours": len(df),
        "train_hours": len(X_train),
        "test_hours": len(X_test),
        "target_unit": "kWh",
        "residual_stats": {
            "mean": round(residual_mean, 2),
            "std": round(residual_std, 2),
            "anomaly_threshold_3sigma_kwh": round(3 * residual_std, 2)
        },
        "feature_importances": feature_importances,
        "baseline_persistence_24h": {
            "rmse": round(base_rmse, 2),
            "mae": round(base_mae, 2),
            "r2": round(base_r2, 4),
            "mape_pct": round(base_mape, 2)
        },
        "xgboost_model": {
            "rmse": round(xgb_rmse, 2),
            "mae": round(xgb_mae, 2),
            "r2": round(xgb_r2, 4),
            "mape_pct": round(xgb_mape, 2)
        }
    }

    metrics_path = os.path.join(current_dir, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print("Energy forecasting model trained successfully!")
    print(f"Baseline: RMSE={base_rmse:.2f}, MAE={base_mae:.2f}, R2={base_r2:.4f}, MAPE={base_mape:.2f}%")
    print(f"XGBoost:  RMSE={xgb_rmse:.2f}, MAE={xgb_mae:.2f}, R2={xgb_r2:.4f}, MAPE={xgb_mape:.2f}%")
    print("Residual Std for 3-Sigma:", residual_std)

if __name__ == "__main__":
    train_and_evaluate()
