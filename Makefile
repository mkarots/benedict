.PHONY: help install install-dev sync sync-dev run test test-cov lint typecheck pre-commit pre-commit-install clean format check deps venv setup recreate-env build publish-test publish

# Default target
help:
	@echo "Benedict - Makefile Commands"
	@echo "============================"
	@echo ""
	@echo "Setup:"
	@echo "  make setup              - Complete dev environment setup (venv + all deps)"
	@echo "  make install            - Install production dependencies only"
	@echo "  make install-dev        - Install all dependencies including dev tools"
	@echo "  make sync               - Sync production dependencies with uv"
	@echo "  make sync-dev           - Sync all dependencies including dev tools"
	@echo "  make deps               - Check if dependencies are installed"
	@echo "  make recreate-env       - Remove and recreate virtual environment"
	@echo "  make pre-commit-install - Install git pre-commit hooks"
	@echo ""
	@echo "Running:"
	@echo "  make run                - Run the bot"
	@echo ""
	@echo "Development:"
	@echo "  make test               - Run pytest"
	@echo "  make test-cov           - Run pytest with coverage"
	@echo "  make format             - Format code (black + ruff)"
	@echo "  make lint               - Lint with ruff"
	@echo "  make typecheck          - Type check with mypy"
	@echo "  make pre-commit         - Run pre-commit on all files"
	@echo "  make check              - Format + tests"
	@echo ""
	@echo "Package:"
	@echo "  make build              - Build sdist and wheel"
	@echo "  make publish-test       - Upload to TestPyPI"
	@echo "  make publish            - Upload to PyPI"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean              - Remove cache files and generated files"
	@echo ""


check-uv:
	@if ! command -v uv > /dev/null; then \
		echo "❌ uv not found. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"; \
		exit 1; \
	fi

# Install dependencies (production only)
install: check-uv
	@echo "Installing dependencies with uv..."
	uv pip install -e .
	@echo "✅ Dependencies installed"

# Install all dependencies including dev tools
install-dev: check-uv
	@echo "Installing all dependencies (including dev tools) with uv..."
	uv pip install -e ".[dev]"
	@echo "✅ All dependencies (including dev tools) installed"

# Check if dependencies are installed
deps:
	@echo "Checking dependencies..."
	@python3 -c "import slack_bolt; print('✅ slack-bolt')" || echo "❌ slack-bolt not installed"
	@python3 -c "import dotenv; print('✅ python-dotenv')" || echo "❌ python-dotenv not installed"
	@python3 -c "import anthropic; print('✅ anthropic')" || echo "❌ anthropic not installed"
	@python3 -c "import sentence_transformers; print('✅ sentence-transformers')" || echo "❌ sentence-transformers not installed"
	@python3 -c "import chromadb; print('✅ chromadb')" || echo "❌ chromadb not installed"

# Run the bot
run:
	@echo "Starting Slack Repo Agent..."
	@if [ ! -f .env ]; then \
		echo "⚠️  Warning: .env file not found. Copy .env.example and add SLACK_BOT_TOKEN and SLACK_APP_TOKEN"; \
	fi
	python3 -m benedict.main

# Run tests
test: check-uv
	@echo "Running tests..."
	uv run pytest tests/

test-cov: check-uv
	@echo "Running tests with coverage..."
	uv run pytest tests/ --cov=src/benedict --cov-report=term-missing --cov-report=html

lint: check-uv
	@echo "Linting..."
	uv run ruff check src tests

typecheck: check-uv
	@echo "Type checking..."
	uv run mypy src/benedict

pre-commit: check-uv
	uv run pre-commit run --all-files

pre-commit-install: check-uv
	uv run pre-commit install

ruff:
	@echo "Linting with ruff..."
	ruff check src tests
	@echo "✅ Ruff complete"

black:
	@echo "Formatting code..."
	black src tests
	@echo "✅ Code formatted"

format: black ruff
check: format test

build: check-uv
	uv run python -m build
	uv run twine check dist/*

publish-test: build
	uv run twine upload --repository testpypi dist/*

publish: build
	uv run twine upload dist/*

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage dist build *.egg-info

setup: check-uv
	uv venv
	uv pip install -e ".[dev]"
	@echo "✅ Development environment ready"
	@echo "Activate with: source .venv/bin/activate"

venv: check-uv
	uv venv
	@echo "✅ Virtual environment created"
	@echo "Activate with: source .venv/bin/activate"

# Sync dependencies (uv's recommended way - same as install but clearer intent)
sync:
	@echo "Syncing dependencies with uv..."
	@if ! command -v uv > /dev/null; then \
		echo "❌ uv not found. Install it with: curl -LsSf https://astral.sh/uv/install.sh | sh"; \
		exit 1; \
	fi
	uv pip install -e .
	@echo "✅ Dependencies synced"


# Sync all dependencies including dev tools
sync-dev: check-uv
	@echo "Syncing all dependencies (including dev tools) with uv..."
	uv pip install -e ".[dev]"
	@echo "✅ All dependencies (including dev tools) synced"

# Recreate virtual environment (nuke and rebuild)
recreate-env: check-uv
	@echo "Recreating virtual environment..."
	uv venv
	@echo "✅ Virtual environment recreated"
	@echo "Activate with: source .venv/bin/activate"
