.PHONY: up down logs demo contract-test proofs eval train report test clean

up:
	docker compose up -d --build

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=50

demo:
	python3 scripts/run_e2e.py --mode demo

contract-test:
	python3 scripts/run_e2e.py --mode demo --strict

proofs:
	bash scripts/collect_proofs.sh

eval:
	python3 scripts/eval.py

train:
	python3 scripts/train.py

test:
	python3 -m pytest tests/ -v

report:
	python3 scripts/build_docx.py

clean:
	rm -rf artifacts data/storage models
