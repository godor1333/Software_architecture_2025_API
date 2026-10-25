import time
from ..models import MeterReadingEvent, EnergyForecastRequest
from ..api.main import pipeline, repository, dispatch_observer, forecasting_strategy

def run_telemetry_simulation():
    print("=" * 75)
    print("  ДЕМОНСТРАЦИЯ: IoT-ТЕЛЕМЕТРИЯ, ПРОГНОЗ И ДЕТЕКЦИЯ ПИКОВ НАГРУЗКИ")
    print("=" * 75)

    building_id = "CAMPUS-BUILDING-A"
    print(f"Объект мониторинга: {building_id} (Учебный корпус, 15 000 кв. м)")

    # 1. Симуляция суточного профиля (24 часа)
    # Ночь: ~200-250 кВт, Утро: ~450-600 кВт, День: ~650-750 кВт, Аварийный пик в 14:00: 920 кВт!
    hourly_profiles = [
        (0, 210.0, 12.0), (1, 205.0, 11.5), (2, 198.0, 11.0), (3, 202.0, 10.8),
        (4, 215.0, 10.5), (5, 240.0, 11.0), (6, 310.0, 12.5), (7, 430.0, 14.0),
        (8, 560.0, 16.5), (9, 680.0, 18.0), (10, 710.0, 19.5), (11, 725.0, 21.0),
        (12, 690.0, 22.0), (13, 705.0, 22.5),
        (14, 920.0, 23.0), # АВАРИЙНЫЙ ПИК!
        (15, 715.0, 22.5), (16, 680.0, 21.5), (17, 590.0, 20.0), (18, 480.0, 18.5),
        (19, 390.0, 17.0), (20, 320.0, 15.5), (21, 280.0, 14.5), (22, 245.0, 13.5),
        (23, 225.0, 13.0)
    ]

    base_time = 1715414400.0 # 00:00

    print("\n[1] Потоковый прием показаний счетчиков за 24 часа...")
    for h, actual_pwr, temp in hourly_profiles:
        ts = base_time + (h * 3600)
        ev = MeterReadingEvent(
            building_id=building_id,
            timestamp=ts,
            meter_reading_kwh=actual_pwr,
            outside_temp_c=temp,
            humidity_pct=50.0
        )
        alert = pipeline.execute(ev)

        tag = f"[{alert.severity.value}]"
        if alert.severity.value != "NORMAL":
            print(f"[{h:02d}:00] {tag:<15} Мощность: {actual_pwr:0.1f} кВт | Прогноз: {alert.predicted_kwh:0.1f} кВт | Z-Score: {alert.z_score:0.1f} sigma -> {alert.reason[:42]}...")
        else:
            if h in [0, 8, 12, 18, 23]:
                print(f"[{h:02d}:00] {tag:<15} Мощность: {actual_pwr:0.1f} кВт | Прогноз: {alert.predicted_kwh:0.1f} кВт (Норма)")

    # 2. Построение прогноза на следующие 6 часов
    print("\n" + "-" * 75)
    print("  ПРОГНОЗ ЭНЕРГОПОТРЕБЛЕНИЯ НА СЛЕДУЮЩИЕ 6 ЧАСОВ (XGBoost)")
    print("-" * 75)
    history = repository.get_recent_history(building_id, limit=24)
    pts, peak = forecasting_strategy.forecast_next_hours(
        current_kwh=history[-1],
        start_hour=0,
        day_of_week=3,
        temp_c=12.0,
        humidity_pct=55.0,
        horizon_hours=6,
        history_24h=history
    )
    for p in pts:
        print(f"  +0{p.hour_offset}ч вперед: {p.predicted_kwh:0.1f} кВт (Доверительный интервал 95%: [{p.expected_lower_bound:0.1f} ... {p.expected_upper_bound:0.1f}] кВт)")
    print(f"Ожидаемый пик на горизонте: {peak:0.1f} кВт")

    # 3. Итоговая аналитика
    print("\n" + "=" * 75)
    print("  СВОДНАЯ СТАТИСТИКА ЗДАНИЯ")
    print("=" * 75)
    stats = repository.get_building_stats(building_id)
    print(f"Всего измерений телеметрии:   {stats.total_telemetry_points}")
    print(f"Текущая мощность:             {stats.current_power_kwh:.1f} кВт")
    print(f"Среднее потребление:          {stats.avg_power_kwh:.1f} кВт")
    print(f"Зафиксированный максимум:     {stats.historical_peak_kwh:.1f} кВт")
    print(f"Выявлено аномальных пиков:    {stats.anomalies_detected}")
    print(f"Передано алертов диспетчеру:  {len(dispatch_observer.dispatched_alerts)}")
    print("=" * 75)

if __name__ == "__main__":
    run_telemetry_simulation()
