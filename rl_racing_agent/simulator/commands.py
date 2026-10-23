class Command:
    def execute(self):
        raise NotImplementedError


class ThrottleCommand(Command):
    def __init__(self, env, amount):
        self.env = env
        self.amount = amount

    def execute(self):
        self.env._accel = self.amount * 10.0


class BrakeCommand(Command):
    def __init__(self, env, amount):
        self.env = env
        self.amount = amount

    def execute(self):
        self.env._accel = -self.amount * 15.0


class SteerCommand(Command):
    def __init__(self, env, amount):
        self.env = env
        self.amount = amount

    def execute(self):
        self.env._steer = self.amount


class CommandInvoker:
    def execute(self, command: Command):
        command.execute()