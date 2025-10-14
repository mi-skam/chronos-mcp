# Migration Guide

This document describes the major tooling and structure changes made to chronos-mcp and how to adapt to them.

## Overview of Changes

We've modernized the project tooling and structure:

1. **Makefile → justfile** - Switched to `just` for better task running
2. **flake8 + isort → ruff** - Consolidated linting with faster tooling
3. **Flat layout → src/ layout** - Adopted standard Python packaging structure
4. **Updated CI/CD** - All workflows updated for new structure

---

## 1. Task Runner: Makefile → justfile

### Why?
- **just** is more modern, faster, and has better cross-platform support
- Simpler syntax with better error messages
- Variables and recipes are more intuitive

### Migration Guide

| Old (Make) | New (just) | Notes |
|------------|------------|-------|
| `make dev-install` | `just dev-install` | Same behavior |
| `make format` | `just format` | Now uses ruff + black |
| `make lint` | `just lint` | Now uses ruff |
| `make test` | `just test` | Same behavior |
| `make test-unit` | `just test-unit` | Same behavior |
| `make coverage` | `just coverage` | Same behavior |
| `make clean` | `just clean` | Same behavior |
| `make server` | `just server` | Same behavior |
| N/A | `just quick` | **NEW**: Fast pre-commit check |
| N/A | `just ci` | **NEW**: Full CI simulation locally |
| N/A | `just complexity` | **NEW**: Check cyclomatic complexity |
| N/A | `just security` | **NEW**: Run security scans |

### Installing just

```bash
# macOS
brew install just

# Linux
cargo install just
# or
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin

# Windows
scoop install just
# or
cargo install just
```

### New Workflow

```bash
# Before committing
just format      # Format code
just quick       # Fast check (format + lint + unit tests)

# Before pushing
just ci          # Full CI simulation locally

# Show all available commands
just --list
```

---

## 2. Linting: flake8 + isort → ruff

### Why?
- **ruff** is 10-100x faster than traditional linters
- Replaces flake8, isort, and more in a single tool
- Auto-fix capabilities built-in
- Better error messages

### Migration Guide

| Old Tools | New Tool | Notes |
|-----------|----------|-------|
| `flake8 chronos_mcp` | `ruff check src/chronos_mcp` | Faster, more rules |
| `isort chronos_mcp` | `ruff check src/chronos_mcp --select I` | Import sorting |
| N/A | `ruff format src/chronos_mcp` | **NEW**: Ruff formatter |
| `black chronos_mcp` | `black src/chronos_mcp` | Still supported |

### Configuration

All configuration is now in `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py310"
line-length = 88
src = ["src"]

[tool.ruff.lint]
select = ["E", "W", "F", "I", "N", "UP", "B", "C4", "SIM", "TCH", "RUF"]
ignore = ["E501", "E203", "W503"]
```

### Pre-commit Hooks

The `.pre-commit-config.yaml` has been updated to use ruff:

```yaml
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.8.0
  hooks:
    - id: ruff
      args: [--fix]
    - id: ruff-format
```

### Fixing Issues

```bash
# Auto-fix issues
just format
# or
ruff check src/chronos_mcp --fix

# Check without fixing
ruff check src/chronos_mcp
```

---

## 3. Project Structure: Flat → src/ Layout

### Why?
- **src/ layout** is the modern Python packaging standard
- Better import isolation during development
- Clearer separation between package and tooling
- Prevents accidental imports from development directory

### Structure Changes

**Before:**
```
chronos-mcp/
├── chronos_mcp/         # Package at root
│   ├── server.py
│   ├── accounts.py
│   └── ...
├── tests/
├── Makefile
└── pyproject.toml
```

**After:**
```
chronos-mcp/
├── src/
│   └── chronos_mcp/     # Package under src/
│       ├── server.py
│       ├── accounts.py
│       └── ...
├── tests/
├── justfile             # Replaces Makefile
└── pyproject.toml
```

### Import Changes

**No changes needed!** Imports remain the same:

```python
from chronos_mcp.accounts import AccountManager
from chronos_mcp.models import Account
```

The `src/` directory is automatically added to the Python path via `pyproject.toml`:

```toml
[tool.setuptools]
packages = ["chronos_mcp"]
package-dir = {"" = "src"}
```

### Testing Changes

**pytest.ini** updated to include `src/` in Python path:

```ini
[tool:pytest]
pythonpath = src
testpaths = tests
```

### Path Updates

All tool commands now reference `src/chronos_mcp`:

```bash
# Linting
ruff check src/chronos_mcp tests

# Type checking
mypy src/chronos_mcp

# Coverage
pytest --cov=src/chronos_mcp
```

---

## 4. Coverage Improvements

### Current Status
- **Current Coverage**: ~77%
- **Target**: 75%+ (maintained)
- **Aspirational**: 85%+

### Coverage Gaps

Priority areas for improvement:

1. **bulk.py**: 40% → 75%
   - Add tests for bulk operations
   - Test error handling modes
   - Test rollback scenarios

2. **tools/events.py**: 44% → 75%
   - Add tests for edge cases
   - Test all event tool functions
   - Test error paths

3. **tools/calendars.py**: 51% → 75%
   - Add tests for calendar tools
   - Test all tool parameters
   - Test error conditions

### Running Coverage

```bash
# Generate coverage report
just coverage

# View HTML report
open htmlcov/index.html

# Check specific module
pytest tests/unit/test_bulk.py --cov=src/chronos_mcp/bulk.py --cov-report=term-missing
```

---

## 5. CI/CD Updates

### GitHub Actions Changes

All workflows updated to use new structure:

#### **test.yml**
```yaml
# Old
- run: black --check chronos_mcp tests
- run: pytest --cov=chronos_mcp

# New
- run: ruff check src/chronos_mcp tests
- run: ruff format src/chronos_mcp tests --check
- run: pytest --cov=src/chronos_mcp
```

#### **ci.yml**
```yaml
# Old
- run: flake8 chronos_mcp tests
- run: isort --check-only chronos_mcp tests

# New
- run: ruff check src/chronos_mcp tests
- run: black --check src/chronos_mcp tests
```

### New CI Features

- **Ruff linting**: Fast linting with auto-fix on pre-commit
- **Ruff formatting**: Additional formatting check
- **Complexity checks**: Radon cyclomatic complexity monitoring
- **Security scans**: Bandit + Safety in CI

---

## 6. Development Workflow Changes

### Old Workflow

```bash
# Setup
make dev-install

# Development
make format
make lint
make test

# Commit
git add .
git commit
```

### New Workflow

```bash
# Setup
just dev-install

# Development
just format        # Format with ruff + black
just lint          # Check with ruff + mypy
just test          # Run tests

# Quick check before commit
just quick         # Format + lint + unit tests

# Commit (pre-commit hooks run automatically)
git add .
git commit

# Before push
just ci            # Full CI simulation locally
```

### Pre-commit Hooks

Pre-commit hooks now run:
1. **ruff linter** with auto-fix
2. **ruff formatter**
3. **black** formatter
4. **mypy** type checking
5. Standard checks (trailing whitespace, YAML, etc.)

Install hooks:
```bash
just dev-install
# or manually
pre-commit install
```

---

## 7. Common Issues & Solutions

### Issue: `ModuleNotFoundError: No module named 'chronos_mcp'`

**Solution**: Reinstall in editable mode:
```bash
pip install -e .
# or
just dev-install
```

### Issue: `pytest` can't find modules

**Solution**: Ensure `pytest.ini` has `pythonpath = src`:
```ini
[tool:pytest]
pythonpath = src
```

### Issue: `just: command not found`

**Solution**: Install just:
```bash
# macOS
brew install just

# Other platforms - see section 1 above
```

### Issue: Ruff errors about unknown rules

**Solution**: Update ruff:
```bash
pip install --upgrade ruff
# or
just dev-install
```

### Issue: Pre-commit hooks failing

**Solution**: Update hooks:
```bash
pre-commit autoupdate
pre-commit run --all-files
```

---

## 8. Backwards Compatibility

### Makefile

The old `Makefile` is **deprecated but still works** for transition period:

```bash
# Still works (deprecated)
make test

# Use instead (recommended)
just test
```

**Plan**: Remove Makefile in v3.0.0

### Import Paths

All import paths remain unchanged:
```python
# Still works ✅
from chronos_mcp.accounts import AccountManager
from chronos_mcp.models import Event
```

### API

No API changes - all tools remain the same.

---

## 9. Benefits Summary

### Performance
- **Ruff**: 10-100x faster linting
- **just**: Faster task execution
- **src/ layout**: Better build/install performance

### Developer Experience
- **just**: Better error messages, clearer syntax
- **Ruff**: Auto-fix most issues
- **Pre-commit**: Catch issues before CI

### Code Quality
- **More lint rules**: Ruff adds many new checks
- **Better complexity tracking**: Radon integration
- **Security**: Automated security scanning

### CI/CD
- **Faster CI**: Ruff speeds up CI significantly
- **Better feedback**: Clearer error messages
- **Local simulation**: `just ci` runs full CI locally

---

## 10. Migration Checklist

For developers upgrading to the new structure:

- [ ] Install `just`: `brew install just` (or see section 1)
- [ ] Update pre-commit hooks: `pre-commit autoupdate`
- [ ] Reinstall package: `just dev-install`
- [ ] Test imports: `python -c "import chronos_mcp; print(chronos_mcp.__file__)"`
- [ ] Run tests: `just test`
- [ ] Run full CI locally: `just ci`
- [ ] Update IDE/editor settings:
  - [ ] Set Python path to include `src/`
  - [ ] Configure linter to use `ruff`
  - [ ] Update test discovery paths
- [ ] Update documentation references from `make` to `just`
- [ ] Commit with new pre-commit hooks

---

## 11. Questions?

See:
- [justfile](justfile) - All available commands
- [CLAUDE.md](CLAUDE.md) - Development guide
- [pyproject.toml](pyproject.toml) - Configuration
- [GitHub Issues](https://github.com/democratize-technology/chronos-mcp/issues) - Report issues
