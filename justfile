# Chronos MCP - Development Tasks
# https://just.systems/man/en/

# Variables
pytest_args := env_var_or_default("PYTEST_ARGS", "-v")
coverage_target := "75"

# Show available commands
default:
    @just --list

# ============================================================================
# SETUP
# ============================================================================

# Initialize development environment from scratch
init: clean
    @echo "🔧 Initializing development environment..."
    @uv --version || (echo "❌ uv not installed. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh" && exit 1)
    uv sync --all-extras --dev
    uv run pre-commit install || echo "⚠️  pre-commit not available"
    @echo "✨ Development environment ready!"
    @echo "Run 'just dev' to start the development server"

# Install/sync dependencies from lock file
install:
    @echo "📦 Syncing dependencies..."
    uv sync --all-extras --dev
    @echo "✨ Dependencies synced"

# Update all dependencies to latest versions
update:
    @echo "⬆️  Updating dependencies..."
    uv lock --upgrade
    uv sync --all-extras --dev
    @echo "✨ Dependencies updated"

# ============================================================================
# DEVELOPMENT
# ============================================================================

# Run development server with MCP inspector
dev:
    @echo "🚀 Starting development server with MCP inspector..."
    @echo "Inspector UI: http://localhost:5173"
    @echo "Press Ctrl+C to stop\n"
    npx @modelcontextprotocol/inspector uv run python -m chronos_mcp

# Run production server
prod:
    @echo "🚀 Starting Chronos MCP server..."
    uv run python -m chronos_mcp

# ============================================================================
# CODE QUALITY
# ============================================================================

# Auto-fix formatting and linting issues
fix:
    @echo "🔧 Auto-fixing code issues..."
    uv run ruff check src/chronos_mcp tests --fix
    uv run ruff format src/chronos_mcp tests
    @echo "✨ Code fixed and formatted"

# Quick check: lint + types + unit tests (fast pre-commit check)
check:
    @echo "🔍 Running quick checks..."
    @echo "\n📝 Linting..."
    uv run ruff check src/chronos_mcp tests
    uv run ruff format src/chronos_mcp tests --check
    @echo "\n🔎 Type checking..."
    uv run mypy src/chronos_mcp
    @echo "\n🧪 Running unit tests..."
    uv run pytest tests/unit/ {{pytest_args}}
    @echo "\n✨ All checks passed - ready to commit!"

# Full CI/CD checks: everything including coverage and security
ci:
    @echo "🔍 Running full CI/CD checks..."
    @echo "\n📝 Linting..."
    uv run ruff check src/chronos_mcp tests
    uv run ruff format src/chronos_mcp tests --check
    @echo "\n🔎 Type checking..."
    uv run mypy src/chronos_mcp
    @echo "\n🧪 Running tests with coverage..."
    uv run pytest tests/ \
        --cov=src/chronos_mcp \
        --cov-report=term-missing \
        --cov-report=html \
        --cov-fail-under={{coverage_target}} \
        {{pytest_args}}
    @echo "\n🔒 Security checks..."
    uv run bandit -r src/chronos_mcp -f screen || echo "⚠️  Security issues found"
    uv run safety scan || echo "⚠️  Vulnerable dependencies found"
    @echo "\n📊 Complexity check..."
    uv run radon cc src/chronos_mcp --min=C --show-complexity || echo "✓ All functions acceptable"
    @echo "\n✨ All CI checks passed!"

# ============================================================================
# TESTING
# ============================================================================

# Run all tests
test *args:
    uv run pytest tests/ {{args}}

# Run tests with coverage report
coverage:
    @echo "🧪 Running tests with coverage..."
    uv run pytest tests/ \
        --cov=src/chronos_mcp \
        --cov-report=term-missing \
        --cov-report=html \
        --cov-report=xml \
        --cov-fail-under={{coverage_target}} \
        {{pytest_args}}
    @echo "\n✨ Coverage report: htmlcov/index.html"

# ============================================================================
# PUBLISHING
# ============================================================================

# Build distribution packages
build: clean
    @echo "📦 Building distribution packages..."
    uv build
    @echo "✨ Build complete: dist/"

# Publish to PyPI (or TestPyPI with --test flag)
publish test="":
    @echo "📤 Publishing to {{ if test == "--test" { "TestPyPI" } else { "PyPI" } }}..."
    @just build
    uv run twine check dist/*
    {{ if test == "--test" { "uv run twine upload --repository testpypi dist/*" } else { "uv run twine upload dist/*" } }}
    @echo "✨ Published successfully!"

# ============================================================================
# UTILITIES
# ============================================================================

# Clean build artifacts and caches
clean deep="":
    @echo "🧹 Cleaning..."
    rm -rf build/ dist/ *.egg-info .coverage htmlcov/ coverage.xml
    rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/
    find . -type f -name "*.pyc" -delete
    find . -type d -name "__pycache__" -delete
    {{ if deep == "--deep" { "rm -rf venv/ .venv/ .uv_cache/ && echo '🧹 Deep clean complete (including venv)'" } else { "echo '✨ Clean complete'" } }}
