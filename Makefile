.PHONY: help install build test lint typecheck format check lua-check

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip

help:
	@echo "make install    Install the SDK and development dependencies"
	@echo "make build      Build the Python wheel and sdist"
	@echo "make test       Run Python tests"
	@echo "make lint       Run Ruff checks"
	@echo "make typecheck  Run Pyright strict checks"
	@echo "make format     Format Python sources"
	@echo "make check      Run lint, format check, typecheck, and tests"
	@echo "make lua-check  Syntax-check Lua files when a Lua interpreter is installed"

install:
	$(PIP) install -e 'python-client[dev]'

build:
	$(PYTHON) -m build python-client

test:
	$(PYTHON) -m pytest tests/python

lint:
	$(PYTHON) -m ruff check python-client/src tests

typecheck:
	$(PYTHON) -m pyright

format:
	$(PYTHON) -m ruff format python-client/src tests

check:
	$(PYTHON) -m ruff check python-client/src tests
	$(PYTHON) -m ruff format --check python-client/src tests
	$(PYTHON) -m pyright
	$(PYTHON) -m pytest tests/python

lua-check:
	@command -v luac >/dev/null || { echo "luac is not installed; skipping Lua syntax check"; exit 0; }; \
	find hammerspoon tests/lua -name '*.lua' -print0 | xargs -0 -n1 luac -p; \
	if command -v lua >/dev/null; then lua tests/lua/test_module_layout.lua; else echo "lua is not installed; skipping Lua behavior tests"; fi
