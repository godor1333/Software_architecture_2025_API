"""Metrics API: чтение агрегатов обучения из PostgreSQL."""
import logging

from fastapi import FastAPI, HTTPException, Query

from src.common.config import settings
from src.common.log import setup

log = setup()
app = FastAPI(title="Pong RL Metrics API", version="1.0.0")


def _conn():
    import psycopg2

    return psycopg2.connect(settings.postgres_dsn)


@app.get("/health")
def health():
    try:
        _conn().close()
        return {"status": "ok", "postgres": "ok"}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"postgres unavailable: {exc}")


@app.get("/experiments")
def experiments():
    sql = """SELECT experiment_id,
                    COUNT(*) AS episodes,
                    MIN(episode) AS first_episode,
                    MAX(episode) AS last_episode,
                    ROUND(AVG(reward)::numeric, 3) AS avg_reward
             FROM episodes GROUP BY experiment_id ORDER BY experiment_id"""
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    return {"experiments": [
        {"experiment_id": r[0], "episodes": r[1], "first_episode": r[2],
         "last_episode": r[3], "avg_reward": float(r[4])} for r in rows]}


@app.get("/episodes")
def episodes(
    experiment_id: str = Query(...),
    limit: int = Query(200, le=2000),
):
    sql = """SELECT episode, steps, reward, epsilon
             FROM episodes WHERE experiment_id = %s
             ORDER BY episode LIMIT %s"""
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (experiment_id, limit))
        rows = cur.fetchall()
    if not rows:
        raise HTTPException(404, "experiment not found")
    return {"experiment_id": experiment_id, "episodes": [
        {"episode": r[0], "steps": r[1], "reward": float(r[2]),
         "epsilon": float(r[3])} for r in rows]}


@app.get("/summary")
def summary(experiment_id: str = Query(...)):
    sql = """SELECT reward, steps FROM episodes
             WHERE experiment_id = %s ORDER BY episode"""
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (experiment_id,))
        rows = cur.fetchall()
    if not rows:
        raise HTTPException(404, "experiment not found")
    rewards = [float(r[0]) for r in rows]
    k = min(50, max(1, len(rewards) // 5))
    return {
        "experiment_id": experiment_id,
        "episodes_total": len(rewards),
        "mean_reward_first_50": round(sum(rewards[:k]) / k, 3),
        "mean_reward_last_50": round(sum(rewards[-k:]) / k, 3),
        "improvement": round(sum(rewards[-k:]) / k - sum(rewards[:k]) / k, 3),
        "best_episode_reward": max(rewards),
    }
