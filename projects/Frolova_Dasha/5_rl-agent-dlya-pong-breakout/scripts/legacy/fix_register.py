import re, pathlib

patched = []
for p in pathlib.Path(".").rglob("*.py"):
    if any(x in str(p) for x in ("venv", ".git", "node_modules")):
        continue
    s = p.read_text()
    if ("ALE/" not in s and "ale_py" not in s) or "register_envs" in s:
        continue
    m = re.search(r"^import gymnasium(?:\s+as\s+(\w+))?", s, re.M)
    if not m:
        continue
    alias = m.group(1) or "gymnasium"
    if "import ale_py" not in s:
        s = s.replace(m.group(0), m.group(0) + "\nimport ale_py", 1)
    s = s.replace(
        m.group(0),
        m.group(0)
        + f'\nif hasattr({alias}, "register_envs"):\n    {alias}.register_envs(ale_py)',
        1,
    )
    p.write_text(s)
    patched.append(str(p))

print("Патч применён к:", patched or "— ни одного файла не найдено —")
