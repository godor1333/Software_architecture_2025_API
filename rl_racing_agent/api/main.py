from fastapi import FastAPI
from pydantic import BaseModel
from agent.factory import AgentFactory
from simulator.env import RacingEnv
from streaming.producer import TelemetryProducer
from streaming.events import TelemetryEvent
import numpy as np

app = FastAPI(title="RL Racing Agent Service")

# Online inference: загружаем обученную модель
env = RacingEnv(render_mode=None)
model = AgentFactory.load("ppo", "models/ppo_racing_final.zip")

producer = TelemetryProducer()
obs, _ = env.reset()
episode = 0
step = 0


class ActionRequest(BaseModel):
    obs: list[float]


class ActionResponse(BaseModel):
    action: list[float]


@app.post("/predict", response_model=ActionResponse)
def predict(req: ActionRequest):
    """Online inference: принимает observation, возвращает действие."""
    action, _ = model.predict(np.array(req.obs, dtype=np.float32), deterministic=True)
    return ActionResponse(action=action.tolist())


@app.post("/step")
def step_simulation():
    """Один шаг симуляции с отправкой телеметрии в Kafka."""
    global obs, step, episode

    action, _ = model.predict(obs, deterministic=True)
    obs, reward, terminated, truncated, info = env.step(action)
    step += 1

    event = TelemetryEvent(
        episode=episode,
        step=step,
        reward=float(reward),
        speed=float(obs[3]),
        progress=float(info["progress"]),
        crashed=info["crashed"],
    )
    producer.send(event)

    if terminated or truncated:
        episode += 1
        step = 0
        obs, _ = env.reset()

    return {"reward": float(reward), "crashed": info["crashed"]}


@app.get("/health")
def health():
    return {"status": "ok"}