# Makefile
# Build & test commands for Loom project

.PHONY: help install test test-unit test-integration test-coverage clean lint format

# default target shows help
help:
	@echo "Available commands:"
	@echo "  install       Install dependencies"
	@echo "  test          Run all tests"
	@echo "  test-unit     Run unit tests only"
	@echo "  test-integration  Run integration tests only"
	@echo "  test-coverage     Run tests w/ coverage report"
	@echo "  test-fast     Run fast tests only (no slow markers)"
	@echo "  clean         Clean up cache & temp files"
	@echo "  lint          Run linting checks"
	@echo "  format        Format code"

# install dependencies
install:
	pip install -r requirements.txt

# run all tests
test:
	pytest tests/ -v

# run unit tests only
test-unit:
	pytest tests/unit -v

# run integration tests only  
test-integration:
	pytest tests/integration -v

# run tests w/ coverage report
test-coverage:
	pytest tests/ -v --cov=src --cov-report=term-missing --cov-report=html

# run fast tests only (exclude slow markers)
test-fast:
	pytest tests/ -v -m "not slow"

# clean up cache & temp files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml

# run linting (if available)
lint:
	@command -v ruff >/dev/null 2>&1 && ruff check src/ || echo "ruff not installed, skipping lint"
	@command -v mypy >/dev/null 2>&1 && mypy src/ || echo "mypy not installed, skipping type check"

# format code (if available)
format:
	@command -v ruff >/dev/null 2>&1 && ruff format src/ || echo "ruff not installed, skipping format"