import pathlib

p = pathlib.Path("tests/test_patterns.py")
s = p.read_text()
old = """    ACTION_COMMANDS[1].execute(env)  # up
    ACTION_COMMANDS[1].execute(env)
    assert env.left_y == before"""
new = """    ACTION_COMMANDS[2].execute(env)  # отходим от верхней границы
    ACTION_COMMANDS[1].execute(env)  # up
    ACTION_COMMANDS[1].execute(env)
    assert env.left_y == before"""
print("found:", old in s)
if old in s:
    p.write_text(s.replace(old, new, 1))
