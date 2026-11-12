"""Лёгковесный Pong (numpy, без зависимостей) + tabular Q-learning.

Это не основной агент проекта (основной — DQN в docker compose up trainer),
а воспроизводимый smoke-прогон обучения: он проверяет, что стратегия
награды и динамика среды дают обучаемый сигнал. Запускается без docker.

Запуск: python scripts/demo_tabular.py
Выход: docs/training_curve.png, docs/demo_metrics.json
"""
import argparse
import json
import os
import random

GRID = 8
PADDLE_SPEED = 0.6
BALL_SPEED = 0.5


class MiniPong:
    """Упрощённый Pong: 8x8 поле, дискретизируемое в ~2600 состояний."""

    ACTIONS = (-1, 0, +1)

    def __init__(self, seed: int = 0, opponent_error: float = 0.15):
        self.rng = random.Random(seed)
        self.opponent_error = opponent_error
        self.reset()

    def reset(self):
        self.paddle = GRID / 2
        self.opp = GRID / 2
        self.ball_x = GRID / 2
        self.ball_y = GRID / 2
        self.vx = BALL_SPEED * self.rng.choice((-1, 1))
        self.vy = BALL_SPEED * self.rng.choice((-1, 1))
        self.agent_score = 0
        self.opp_score = 0
        return self._state()

    def _state(self):
        return (
            min(int(self.paddle), GRID - 1),
            min(int(self.ball_x), GRID - 1),
            min(int(self.ball_y), GRID - 1),
            0 if self.vx == 0 else (1 if self.vx > 0 else -1),
            0 if self.vy == 0 else (1 if self.vy > 0 else -1),
        )

    def step(self, action: int):
        self.paddle = min(max(self.paddle + self.ACTIONS[action] * PADDLE_SPEED, 0), GRID - 1)
        self.ball_x += self.vx
        self.ball_y += self.vy
        if self.ball_y <= 0 or self.ball_y >= GRID:
            self.vy = -self.vy
            self.ball_y = min(max(self.ball_y, 0), GRID)

        # противник: трекинг с ошибкой
        if self.vx > 0:
            err = self.opponent_error * self.rng.uniform(-2, 2)
            move = BALL_SPEED if self.ball_y > self.opp else -BALL_SPEED
            self.opp = min(max(self.opp + move * (1 if self.rng.random() > 0.15 else 0) + err, 0), GRID - 1)

        reward = 0.0
        if self.ball_x <= 0.5 and self.vx < 0:
            if abs(self.ball_y - self.paddle) <= 0.75:
                self.vx = BALL_SPEED
                self.vy += (self.ball_y - self.paddle) * 0.3
            else:
                self.opp_score += 1
                reward = -1.0
                self.ball_x, self.ball_y = GRID / 2, GRID / 2
                self.vx = BALL_SPEED * self.rng.choice((-1, 1))
                self.vy = BALL_SPEED * self.rng.choice((-1, 1))

        if self.ball_x >= GRID - 0.5 and self.vx > 0:
            if abs(self.ball_y - self.opp) <= 0.75 and self.rng.random() > self.opponent_error:
                self.vx = -BALL_SPEED
            else:
                self.agent_score += 1
                reward = 1.0
                self.ball_x, self.ball_y = GRID / 2, GRID / 2
                self.vx = BALL_SPEED * self.rng.choice((-1, 1))
                self.vy = BALL_SPEED * self.rng.choice((-1, 1))

        done = self.agent_score >= 11 or self.opp_score >= 11
        return self._state(), reward, done


def train(env: MiniPong, total_steps: int, alpha=0.1, gamma=0.99,
          eps_start=1.0, eps_end=0.05):
    q = {}
    rewards, steps_per_ep = [], []
    ep_reward, ep_steps = 0.0, 0
    half = total_steps // 2

    def get(s):
        return q.setdefault(s, [0.0, 0.0, 0.0])

    for t in range(total_steps):
        eps = max(eps_end, eps_start - (eps_start - eps_end) * min(t / half, 1.0))
        s = env._state()
        if random.random() < eps:
            a = random.randrange(3)
        else:
            a = max(range(3), key=lambda i: get(s)[i])
        s2, r, done = env.step(a)
        target = r + (0.0 if done else gamma * max(get(s2)))
        get(s)[a] += alpha * (target - get(s)[a])
        ep_reward += r
        ep_steps += 1
        if done:
            rewards.append(ep_reward)
            steps_per_ep.append(ep_steps)
            ep_reward, ep_steps = 0.0, 0
            env.reset()
    return rewards


def random_baseline(env: MiniPong, n_episodes: int = 100):
    rewards = []
    for _ in range(n_episodes):
        total, done = 0.0, False
        while not done:
            _, r, done = env.step(random.randrange(3))
            total += r
        rewards.append(total)
        env.reset()
    return rewards


def rolling(xs, w):
    out = []
    for i in range(len(xs)):
        lo = max(0, i - w + 1)
        out.append(sum(xs[lo:i + 1]) / (i - lo + 1))
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=120_000)
    args = parser.parse_args()
    random.seed(42)

    env = MiniPong(seed=42)
    baseline = random_baseline(env, 100)
    rewards = train(env, args.steps)

    k = min(50, len(rewards) // 5)
    metrics = {
        "episodes_trained": len(rewards),
        "total_steps": args.steps,
        "mean_reward_first_50": round(sum(rewards[:k]) / k, 3),
        "mean_reward_last_50": round(sum(rewards[-k:]) / k, 3),
        "improvement": round(sum(rewards[-k:]) / k - sum(rewards[:k]) / k, 3),
        "random_baseline_mean": round(sum(baseline) / len(baseline), 3),
        "last_50_score": round(
            sum(1 for r in rewards[-k:] if r > 0) / k, 3),
    }

    os.makedirs("docs", exist_ok=True)
    with open("docs/demo_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(json.dumps(metrics, indent=2))

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(9, 5))
        ax.plot(rolling(rewards, 25), label="Q-learning (MiniPong)")
        ax.axhline(sum(baseline) / len(baseline), color="gray", ls="--",
                   label=f"random baseline ({sum(baseline) / len(baseline):.1f})")
        ax.set_xlabel("эпизод")
        ax.set_ylabel("суммарная награда за эпизод")
        ax.set_title("Обучение агента (лёгковесный прогон, python demo_tabular.py)")
        ax.legend(); ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig("docs/training_curve.png", dpi=130)
        print("saved docs/training_curve.png")
    except Exception as exc:
        print("plot skipped:", exc)


if __name__ == "__main__":
    main()
