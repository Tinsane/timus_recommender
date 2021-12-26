.PHONY : init black-lint flake8 mypy lint pretty tests

CODE = db src bot_main.py
TESTS ?= tests
ALL = $(CODE) $(TESTS)

VENV ?= venv
JOBS ?= 4

pre-init:
	sudo apt install python3.8 python3.8-venv python3.8-dev python3.8-distutils

init:
	python3.8 -m venv $(VENV)
	$(VENV)/bin/python -m pip install --upgrade pip
	$(VENV)/bin/python -m pip install poetry
	$(VENV)/bin/poetry install

lock:
	docker-compose build lock
	docker-compose run --rm lock

black-lint:
	$(VENV)/bin/black --skip-string-normalization --check $(ALL)

flake8:
	$(VENV)/bin/flake8 --jobs $(JOBS) --statistics --show-source $(ALL)

mypy:
	$(VENV)/bin/mypy $(CODE)

lint: black-lint flake8 mypy

pretty:
	$(VENV)/bin/isort $(ALL)
	$(VENV)/bin/black --skip-string-normalization $(ALL)

tests:
	$(VENV)/bin/pytest $(TESTS)