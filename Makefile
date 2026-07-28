.PHONY: test compile lint typecheck ci run demo load-smoke event-contract compose-up compose-down

test:
	PYTHONPATH=src python3 -m unittest discover -s tests

compile:
	PYTHONPYCACHEPREFIX=.pycache_tmp python3 -m compileall src tests scripts

lint:
	python3 -m ruff check src tests scripts

typecheck:
	python3 -m mypy src

ci: test compile

run:
	uvicorn ticketing.main:app --reload --app-dir src

demo:
	python3 scripts/demo_flow.py

load-smoke:
	python3 scripts/load_smoke.py

event-contract:
	PYTHONPATH=src python3 scripts/kafka_event_probe.py

compose-up:
	docker compose up --build

compose-down:
	docker compose down
