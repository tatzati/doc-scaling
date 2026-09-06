PYTHON ?= python3

.PHONY: install test run up down

install:
	$(PYTHON) -m pip install -e '.[test]'

test:
	$(PYTHON) -m pytest

run:
	uvicorn app.main:app --reload

up:
	docker compose up --build

down:
	docker compose down
