import pathlib

p = pathlib.Path("src/training/strategies.py")
s = p.read_text()

s = s.replace(
    "from src.agents.factory import AgentFactory",
    "from stable_baselines3 import DQN, PPO\n\nfrom src.agents.factory import AgentFactory",
)
s = s.replace('    NAME = "DQN"', '    NAME = "DQN"\n    ALGO = DQN')
s = s.replace('    NAME = "PPO"', '    NAME = "PPO"\n    ALGO = PPO')

p.write_text(s)
print("patched:", "ALGO = DQN" in s and "ALGO = PPO" in s and "from stable_baselines3" in s)
