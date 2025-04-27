.PHONY: install dev test test-docker lint format typecheck clean

install:
	pip install -e ".[dev]"

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v --cov=app --cov-report=term-missing

test-docker:
	docker build -f Dockerfile.test -t video-process-test .
	docker run --rm --network host video-process-test

lint:
	ruff check app/ tests/
	black --check app/ tests/

format:
	ruff check --fix app/ tests/
	black app/ tests/

typecheck:
	mypy app/

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name "*.egg" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".ruff_cache" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} + 