from fastapi import FastAPI, Header, HTTPException, Request, Query
from fastapi.responses import HTMLResponse
from html import escape
from starlette.concurrency import run_in_threadpool
import app as service

api = FastAPI(title="Scene Segmentation")

@api.get('/health')
def health(): return {"status":"ok"}

@api.post('/api/v1/frames', status_code=201)
async def frame(request: Request, x_frame_id: str = Header(), x_flight_id: str = Header()):
    body=await request.body()
    if not body: raise HTTPException(422, 'image body is required')
    try: return await run_in_threadpool(service.store_frame,x_frame_id,x_flight_id,body)
    except (ValueError, OSError) as exc: raise HTTPException(422,str(exc)) from exc

@api.get('/api/v1/summary')
def summary(): return service.summary()

@api.get('/api/v1/analytics')
def analytics(flight_id: str | None = Query(default=None)): return service.analytics(flight_id)

@api.get('/dashboard', response_class=HTMLResponse)
def dashboard(flight_id: str | None = Query(default=None)):
    data = service.analytics(flight_id)
    dominant = {}
    for item in data['items']:
        dominant[item['dominant_class']] = dominant.get(item['dominant_class'], 0) + 1
    rows = ''.join(
        f"<tr><td>{escape(item['frame_id'])}</td><td>{escape(item['flight_id'])}</td><td>{escape(item['dominant_class'])}</td>"
        f"<td>{item['road_share']:.4f}</td><td>{item['pedestrian_share']:.4f}</td></tr>"
        for item in data['items'][-20:]
    ) or '<tr><td colspan="5">Нет обработанных кадров</td></tr>'
    bars = ''.join(f'<li><b>{escape(key)}</b><span style="width:{min(value / max(data["frames"], 1) * 80, 80)}%">{value}</span></li>' for key, value in dominant.items())
    mode = 'PostgreSQL' if service.production_enabled() else 'SQLite (локально)'
    events = 'включены' if service.production_enabled() else 'локальный режим'
    return HTMLResponse(f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Scene Analytics Dashboard</title>
<style>body{{font-family:Arial,sans-serif;background:#f4f7fb;color:#172033;margin:0}}main{{max-width:1100px;margin:30px auto;padding:0 24px}}.hero{{background:#153a67;color:white;border-radius:16px;padding:24px 28px}}.cards{{display:flex;gap:16px;margin:18px 0;flex-wrap:wrap}}.card{{background:white;border-radius:12px;padding:18px 22px;box-shadow:0 2px 9px #d8e0eb;min-width:180px}}.value{{font-size:28px;font-weight:bold}}table{{width:100%;border-collapse:collapse;background:white;border-radius:12px;overflow:hidden}}th,td{{padding:10px;border-bottom:1px solid #e6ebf2;text-align:left}}th{{background:#eaf1fb}}ul{{padding:0;list-style:none}}li{{margin:8px 0;background:#e9eef7;padding:8px;border-radius:8px}}li span{{display:inline-block;background:#4a83c5;color:white;margin-left:14px;padding:2px 8px;border-radius:5px}}</style></head>
<body><main><section class="hero"><h1>Scene Analytics Dashboard</h1><p>Сегментация дорожной сцены · flight: {escape(flight_id or 'all')}</p></section>
<section class="cards"><div class="card"><div>Кадров</div><div class="value">{data['frames']}</div></div><div class="card"><div>Хранилище</div><div class="value">{mode}</div></div><div class="card"><div>Kafka</div><div class="value">{events}</div></div></section>
<h2>Доминирующие классы</h2><ul>{bars or '<li>Нет данных</li>'}</ul><h2>Последние кадры</h2><table><thead><tr><th>Frame</th><th>Flight</th><th>Класс</th><th>Road share</th><th>Pedestrian share</th></tr></thead><tbody>{rows}</tbody></table></main></body></html>''')

@api.get('/pipeline', response_class=HTMLResponse)
def pipeline_view(flight_id: str | None = Query(default=None)):
    data = service.analytics(flight_id)
    rows = ''.join(f'<li><b>{escape(item["frame_id"])}</b> → {escape(item["dominant_class"])}; road={item["road_share"]:.4f}; pedestrian={item["pedestrian_share"]:.4f}</li>' for item in data['items'][-12:])
    return HTMLResponse(f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Scene Pipeline</title>
<style>body{{font-family:Arial,sans-serif;background:#111827;color:#f8fafc;margin:0}}main{{max-width:1100px;margin:35px auto;padding:0 28px}}h1{{font-size:34px}}.flow{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:28px 0}}.step{{background:#2563eb;border-radius:12px;padding:18px 22px;font-weight:bold}}.arrow{{font-size:28px;color:#93c5fd}}.panel{{background:#1f2937;border-radius:14px;padding:20px}}li{{padding:8px;border-bottom:1px solid #374151}}</style></head>
<body><main><h1>Video segmentation pipeline</h1><p>Поток flight: {escape(flight_id or 'all')} · обработано кадров: {data['frames']} · режим: {'production' if service.production_enabled() else 'локальный'}</p><div class="flow"><div class="step">Video stream</div><div class="arrow">→</div><div class="step">Preprocessing</div><div class="arrow">→</div><div class="step">SegFormer / color baseline</div><div class="arrow">→</div><div class="step">Scene analytics</div><div class="arrow">→</div><div class="step">Dashboard / Kafka*</div></div><p>*Kafka используется при включённом production-профиле.</p><div class="panel"><h2>Результаты pipeline</h2><ul>{rows or '<li>Нет обработанных кадров</li>'}</ul></div></main></body></html>''')

@api.get('/api/v1/frames/{frame_id}')
def get_frame(frame_id: str):
    result=service.get_frame(frame_id)
    if result is None: raise HTTPException(404,'frame not found')
    return result
