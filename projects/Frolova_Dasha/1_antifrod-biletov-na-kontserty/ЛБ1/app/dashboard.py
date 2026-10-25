from __future__ import annotations

from fastapi.responses import HTMLResponse


def dashboard_page() -> HTMLResponse:
    return HTMLResponse(
        """<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>TicketShield — дашборд антифрода</title>
<style>
body{margin:0;background:#07111f;color:#e7eef8;font:16px/1.45 Arial,sans-serif}.wrap{max-width:1050px;margin:auto;padding:34px}
h1{margin:0 0 6px}.lead{color:#9fb1c8}.status{display:inline-block;background:#0c6646;color:#c8ffe8;padding:5px 11px;border-radius:20px;font-size:13px}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:26px 0}.card{background:#101e31;border:1px solid #213958;border-radius:14px;padding:20px}
.label{color:#9fb1c8;font-size:13px}.value{font-size:30px;font-weight:700;margin-top:8px}.pipeline{background:#101e31;border-radius:14px;padding:22px;margin-top:15px}.flow{display:flex;align-items:center;gap:9px;flex-wrap:wrap}.node{background:#173351;border:1px solid #2c5c8c;border-radius:9px;padding:9px 12px}.arrow{color:#66b7ff;font-size:22px}
.foot{color:#9fb1c8;margin-top:22px;font-size:13px}@media(max-width:720px){.cards{grid-template-columns:repeat(2,1fr)}}
</style></head><body><main class="wrap"><span class="status">● сервис доступен</span><h1>TicketShield: дашборд антифрода</h1><p class="lead">Сводка событий из аналитического хранилища ClickHouse. Автообновление — каждые 2 секунды.</p>
<section class="cards"><div class="card"><div class="label">Всего событий</div><div class="value" id="total">0</div></div><div class="card"><div class="label">На ручной REVIEW</div><div class="value" id="review">0</div></div><div class="card"><div class="label">Доля REVIEW</div><div class="value" id="rate">0%</div></div><div class="card"><div class="label">Средний риск</div><div class="value" id="risk">0</div></div></section>
<section class="pipeline"><h2>Event-driven pipeline</h2><div class="flow"><span class="node">API</span><span class="arrow">→</span><span class="node">Kafka<br>orders.created</span><span class="arrow">→</span><span class="node">Feature Service<br>Redis</span><span class="arrow">→</span><span class="node">Kafka<br>orders.enriched</span><span class="arrow">→</span><span class="node">Scoring<br>LightGBM</span><span class="arrow">→</span><span class="node">PostgreSQL + ClickHouse</span></div></section>
<p class="foot" id="meta">Загрузка...</p></main><script>async function refresh(){try{let x=await fetch('/api/v1/dashboard/summary');let d=await x.json();total.textContent=d.total_events;review.textContent=d.review_events;rate.textContent=(d.review_rate*100).toFixed(2)+'%';risk.textContent=d.average_risk_score.toFixed(4);meta.textContent='Версия модели: '+d.model_version+' • Обновлено: '+new Date().toLocaleTimeString('ru-RU')}catch(e){meta.textContent='Ожидание данных: '+e.message}}refresh();setInterval(refresh,2000)</script></body></html>"""
    )
