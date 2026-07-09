.PHONY: test install lint

install:
	pip install -e ".[dev]"

test:
	pytest -q

lint:
	python -m compileall -q src || python -m compileall -q .
