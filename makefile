CODE = db storage.py bot_main.py loader.py

ALL = $(CODE)


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

lint:
	$(VENV)/bin/black --skip-string-normalization --check $(ALL)
	$(VENV)/bin/flake8 --jobs $(JOBS) --statistics --show-source $(ALL)
	$(VENV)/bin/mypy $(CODE)

mypy:
	$(VENV)/bin/mypy $(CODE)

pretty:
	$(VENV)/bin/isort $(ALL)
	$(VENV)/bin/black --skip-string-normalization $(ALL)

precommit_install:
	@git init
	echo '#!/bin/sh\nmake lint\n' > .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit

clear:
	rm -rf allure-results
	rm -rf profiling_data
	rm -rf .mypy_cache
