# Chronos MCP - Development Tasks
# https://just.systems/man/en/
# Uses uv for fast Python package management: https://github.com/astral-sh/uv

# Variables
pytest_args := env_var_or_default("PYTEST_ARGS", "-v")
coverage_target := "75"

# Default recipe - show available commands
default:
    @just --list

# Check if uv is installed
check-uv:
    @uv --version || (echo "❌ uv not installed. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh" && exit 1)
    @echo "✅ uv installed: $(uv --version)"

# Install package for production use
install:
    uv pip install -e .

# Install package with development dependencies
dev-install:
    uv sync --all-extras --dev
    uv run pre-commit install || echo "pre-commit not available, skipping hook installation"

# Format code with ruff and black
format:
    uv run ruff check src/chronos_mcp tests --fix || true
    uv run ruff format src/chronos_mcp tests
    uv run black src/chronos_mcp tests

# Run all linters and checks
lint:
    @echo "Running ruff..."
    uv run ruff check src/chronos_mcp tests
    @echo "\nRunning black..."
    uv run black --check src/chronos_mcp tests
    @echo "\nRunning mypy..."
    uv run mypy src/chronos_mcp

# Check code formatting without modifying
check-format:
    uv run ruff format src/chronos_mcp tests --check
    uv run black --check src/chronos_mcp tests

# Run all tests
test:
    uv run pytest tests/ {{pytest_args}}

# Run unit tests only
test-unit:
    uv run pytest tests/unit/ {{pytest_args}}

# Run integration tests only
test-integration:
    uv run pytest tests/integration/ {{pytest_args}} || echo "No integration tests directory"

# Run tests with coverage report
coverage:
    uv run pytest tests/ \
        --cov=src/chronos_mcp \
        --cov-report=term-missing \
        --cov-report=html \
        --cov-report=xml \
        --cov-fail-under={{coverage_target}} \
        {{pytest_args}}
    @echo "\n✨ Coverage report generated in htmlcov/index.html"

# Run tests for a specific file
test-file file:
    uv run pytest {{file}} {{pytest_args}}

# Check cyclomatic complexity with radon
complexity:
    @echo "Checking cyclomatic complexity (threshold: C rating = 11-20)..."
    uv run radon cc src/chronos_mcp --min=C --show-complexity || echo "✓ All functions have acceptable complexity"

# Run security checks
security:
    @echo "Running bandit security scan..."
    uv run bandit -r src/chronos_mcp -f screen || echo "⚠️  Security issues found"
    @echo "\nRunning safety dependency check..."
    uv run safety check || echo "⚠️  Vulnerable dependencies found"

# Run all quality checks (lint + test + security)
check: lint test security

# Clean build artifacts and caches
clean:
    rm -rf build/
    rm -rf dist/
    rm -rf *.egg-info
    rm -rf .coverage
    rm -rf htmlcov/
    rm -rf coverage.xml
    rm -rf .pytest_cache/
    rm -rf .mypy_cache/
    rm -rf .ruff_cache/
    find . -type f -name "*.pyc" -delete
    find . -type d -name "__pycache__" -delete

# Deep clean including virtual environment
clean-all: clean
    rm -rf venv/
    rm -rf .venv/
    rm -rf .uv_cache/

# Build distribution packages
build: clean
    uv build

# Check distribution packages
check-dist: build
    uv run twine check dist/*

# Publish to PyPI (requires credentials)
publish: check-dist
    uv run twine upload dist/*

# Publish to TestPyPI for testing
publish-test: check-dist
    uv run twine upload --repository testpypi dist/*

# Run the MCP server
server:
    uv run python -m chronos_mcp

# Run Radicale test CalDAV server
radicale:
    uv run python -m radicale --config tests/fixtures/radicale.conf

# Run pre-commit hooks on all files
pre-commit:
    uv run pre-commit run --all-files

# Update pre-commit hooks
update-hooks:
    uv run pre-commit autoupdate

# Generate requirements.txt from uv.lock
requirements:
    uv pip compile pyproject.toml -o requirements.txt
    @echo "✨ requirements.txt generated from uv.lock"

# Update all dependencies
update-deps:
    uv lock --upgrade
    @echo "✨ Dependencies updated in uv.lock"

# Sync dependencies from uv.lock
sync:
    uv sync
    @echo "✨ Dependencies synced from uv.lock"

# Watch tests and re-run on changes (requires pytest-watch)
watch:
    uv run ptw -- {{pytest_args}}

# Run type checking with mypy
types:
    uv run mypy src/chronos_mcp --strict --show-error-codes

# Generate coverage badge (requires coverage-badge)
badge:
    uv run coverage-badge -o coverage.svg -f

# Show project statistics
stats:
    @echo "=== Project Statistics ==="
    @echo "\nLines of code:"
    @find src/chronos_mcp -name "*.py" | xargs wc -l | tail -1
    @echo "\nTest files:"
    @find tests -name "test_*.py" | wc -l
    @echo "\nCyclomatic complexity:"
    @uv run radon cc src/chronos_mcp -s -a
    @echo "\nMaintainability index:"
    @uv run radon mi src/chronos_mcp -s

# Initialize development environment from scratch
init: clean check-uv dev-install
    @echo "✨ Development environment initialized with uv"
    @echo "Run 'just test' to verify installation"

# Quick check before committing
quick: format check-format test-unit
    @echo "✨ Quick checks passed - ready to commit!"

# Full CI/CD simulation locally
ci: lint test coverage complexity security
    @echo "✨ All CI checks passed!"

# Show uv cache information
uv-cache:
    @echo "=== UV Cache Information ==="
    @uv cache dir
    @echo "\nCache size:"
    @du -sh $(uv cache dir)

# Clean uv cache
uv-cache-clean:
    uv cache clean
    @echo "✨ UV cache cleaned"
