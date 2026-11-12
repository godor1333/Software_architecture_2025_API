import json
import os

BASE = os.path.join(os.path.dirname(__file__), "..")
REPORT = os.path.join(BASE, "report.md")
M = os.path.join(BASE, "artifacts", "metrics.json")

def main():
    if not os.path.exists(M):
        print("нет artifacts/metrics.json - сначала make eval")
        return
    m = json.load(open(M, encoding="utf-8"))
    text = open(REPORT, encoding="utf-8").read()
    text = text.replace("[ЗАПОЛНИТЬ: make eval]", "%s" % m["accuracy"], 1)
    text = text.replace("[ЗАПОЛНИТЬ: make eval]", "%s" % m["macro_f1"], 1)
    open(REPORT, "w", encoding="utf-8").write(text)
    print("report.md обновлён: accuracy=%s macro_f1=%s" % (m["accuracy"], m["macro_f1"]))

if __name__ == "__main__":
    main()
