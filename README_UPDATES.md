# README Updates for New Tooling

These updates should be made to README.md to reflect the new tooling structure.

## Section: Development

### Replace existing "Development" section with:

```markdown
## Development

### Quick Start

```bash
# Install just (task runner)
brew install just  # macOS
# See https://just.systems/man/en/ for other platforms

# Setup development environment
just dev-install

# See all available commands
just --list
```

### Common Commands

```bash
# Format code (required before committing)
just format

# Run linters
just lint

# Run tests
just test

# Run tests with coverage
just coverage

# Quick check before committing (format + lint + unit tests)
just quick

# Full CI simulation locally
just ci
```

### Project Structure

This project uses the **src/ layout** for better packaging:

```
chronos-mcp/
├── src/
│   └── chronos_mcp/     # Main package
│       ├── server.py    # MCP server entry point
│       ├── accounts.py  # Account management
│       ├── calendars.py # Calendar operations
│       ├── events.py    # Event operations
│       ├── tasks.py     # Task operations
│       ├── journals.py  # Journal operations
│       └── tools/       # MCP tool definitions
├── tests/
│   └── unit/            # Unit tests (502 tests)
├── justfile             # Task runner
├── pyproject.toml       # Project configuration
└── pytest.ini           # Test configuration
```

### Development Workflow

```bash
# 1. Make changes to code

# 2. Format and check
just format
just quick  # Fast pre-commit check

# 3. Run full test suite
just test

# 4. Commit (pre-commit hooks run automatically)
git add .
git commit -m "feat: your changes"

# 5. Before pushing
just ci  # Simulate full CI locally
```

### Code Quality Tools

- **Linting**: [ruff](https://docs.astral.sh/ruff/) (10-100x faster than flake8)
- **Formatting**: black + ruff
- **Type Checking**: mypy
- **Testing**: pytest with 75%+ coverage target
- **Complexity**: radon
- **Security**: bandit + safety

### Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality:

```bash
# Hooks are installed automatically with:
just dev-install

# Or manually:
pre-commit install

# Run hooks manually on all files:
just pre-commit
```

Hooks include:
- ruff linter with auto-fix
- ruff formatter
- black formatter
- mypy type checking
- Standard checks (trailing whitespace, YAML, etc.)

### Testing

```bash
# Run all tests
just test

# Run unit tests only
just test-unit

# Run with coverage report
just coverage

# View coverage report
open htmlcov/index.html

# Run specific test file
just test-file tests/unit/test_events.py

# Run specific test
pytest tests/unit/test_events.py::test_create_event -v
```

### Code Quality Checks

```bash
# Run linters
just lint

# Check formatting
just check-format

# Type check
just types

# Check cyclomatic complexity
just complexity

# Security scan
just security

# Run all checks
just check
```

### Migration Guide

If you're upgrading from an earlier version, see [MIGRATION.md](MIGRATION.md) for:
- Makefile → justfile command mapping
- flake8 + isort → ruff migration
- Flat layout → src/ layout changes
- CI/CD updates
- Common issues & solutions
```

## Section: Installation

### Update installation section:

```markdown
## Installation

### Standard Installation

```bash
pip install -e .
```

### Development Installation (Recommended)

Includes all development dependencies (pytest, ruff, black, mypy, etc.):

```bash
# Using just (recommended)
just dev-install

# Or manually
pip install -e ".[dev]"
pre-commit install
```

### Secure Installation

Includes keyring support for secure password storage:

```bash
pip install -e ".[dev]"
```

**Note**: Keyring is included in dev dependencies for secure credential storage.
```

## Section: Add "Tooling" section

```markdown
## Tooling

This project uses modern Python development tools:

- **Task Runner**: [just](https://just.systems/) - Fast, intuitive task runner
- **Linting**: [ruff](https://docs.astral.sh/ruff/) - 10-100x faster than traditional linters
- **Formatting**: black + ruff - Consistent code style
- **Type Checking**: mypy - Static type analysis
- **Testing**: pytest - 502 tests, 77% coverage
- **Pre-commit**: Automated code quality checks
- **CI/CD**: GitHub Actions with cross-platform testing

### Why These Tools?

**just vs Make**:
- Simpler syntax, better error messages
- Cross-platform (Windows, macOS, Linux)
- Faster execution

**ruff vs flake8 + isort**:
- 10-100x faster (written in Rust)
- Replaces multiple tools
- Auto-fix capabilities
- 100+ additional checks

**src/ layout**:
- Industry standard for modern Python
- Better import isolation
- Cleaner packaging

See [TOOLING_SUMMARY.md](TOOLING_SUMMARY.md) for details and performance comparisons.
```

## Section: Add "Resources" section

```markdown
## Resources

### Documentation
- [README.md](README.md) - Project overview
- [CLAUDE.md](CLAUDE.md) - Development guide
- [MIGRATION.md](MIGRATION.md) - Migration from old tooling
- [TOOLING_SUMMARY.md](TOOLING_SUMMARY.md) - Tooling details
- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design
- [API Reference](docs/api/README.md) - Complete API docs

### Quick Links
- [justfile](justfile) - All available commands
- [pyproject.toml](pyproject.toml) - Project configuration
- [.pre-commit-config.yaml](.pre-commit-config.yaml) - Pre-commit hooks
- [GitHub Issues](https://github.com/democratize-technology/chronos-mcp/issues) - Report issues

### External Resources
- [just Manual](https://just.systems/man/en/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [FastMCP](https://github.com/jlowin/fastmcp)
- [CalDAV RFC 4791](https://tools.ietf.org/html/rfc4791)
```

## Section: Update Contributing section

```markdown
## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

### Quick Contribution Guide

1. **Fork the repository**

2. **Clone and setup**:
   ```bash
   git clone https://github.com/your-username/chronos-mcp.git
   cd chronos-mcp
   just dev-install  # Setup development environment
   ```

3. **Create a branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

4. **Make changes and test**:
   ```bash
   just format      # Format code
   just quick       # Fast checks
   just ci          # Full CI simulation
   ```

5. **Commit** (pre-commit hooks run automatically):
   ```bash
   git add .
   git commit -m "feat: your feature description"
   ```

6. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```

### Code Quality Standards

- **Test Coverage**: 75%+ required, 85%+ aspirational
- **Linting**: Must pass `just lint`
- **Formatting**: Auto-formatted with `just format`
- **Type Hints**: Required for public APIs
- **Documentation**: Update docs for new features
- **Complexity**: Keep cyclomatic complexity < C (11-20)

### Development Tools

All checks can be run locally before pushing:

```bash
just ci  # Runs: lint, test, coverage, complexity, security
```
```

## Add badges to top of README

```markdown
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP 2.0+](https://img.shields.io/badge/FastMCP-2.0+-green.svg)](https://github.com/jlowin/fastmcp)
[![CalDAV](https://img.shields.io/badge/CalDAV-RFC4791-orange.svg)](https://tools.ietf.org/html/rfc4791)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
```

---

## Implementation Checklist

- [ ] Update README.md with sections above
- [ ] Add badges to top of README
- [ ] Ensure all links work correctly
- [ ] Update any screenshots/GIFs if present
- [ ] Verify code examples work
- [ ] Check formatting and consistency
- [ ] Update version numbers if needed
