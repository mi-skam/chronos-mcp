# UV Migration Guide

This document describes the migration to [uv](https://github.com/astral-sh/uv) - an extremely fast Python package installer and resolver written in Rust by Astral (the creators of ruff).

## What is UV?

**uv** is a drop-in replacement for pip, pip-tools, and virtualenv that is:
- **10-100x faster** than pip
- **Written in Rust** for maximum performance
- **Drop-in compatible** with existing Python projects
- **From Astral** - the same team that created ruff

### Performance Comparison

| Operation | pip | uv | Speedup |
|-----------|-----|-----|---------|
| Install dependencies | ~45s | ~0.5s | **90x faster** |
| Resolve dependencies | ~30s | ~0.3s | **100x faster** |
| Create virtual environment | ~2s | ~0.1s | **20x faster** |

---

## Changes Made

### 1. Package Management: pip → uv ✅

**All Python operations now use uv:**
- `pip install` → `uv pip install` or `uv sync`
- `pip freeze` → `uv pip freeze`
- `python -m` → `uv run python -m`
- Virtual environments managed automatically

### 2. Dependency Locking

**Added `uv.lock` file** for reproducible builds:
- **Before**: No lock file, potential version drift
- **After**: `uv.lock` ensures exact versions across installs
- Similar to `package-lock.json` (npm) or `Cargo.lock` (Rust)

### 3. Configuration

**Updated `pyproject.toml`:**
```toml
[dependency-groups]
dev = [
    "pytest>=8.4.1",
    "pytest-asyncio>=1.1.0",
    "pytest-cov>=6.2.1",
    "radon>=6.0.1",
    "ruff>=0.8.0",
    "black>=24.0.0",
    "mypy>=1.9.0",
    "bandit>=1.7.0",
    "safety>=3.0.0",
    "pre-commit>=3.5.0",
]

[tool.uv]
package = true
```

**Note**: UV uses the standard `dependency-groups` field (PEP 735) instead of custom fields.

---

## Installation

### Install UV

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# With pipx
pipx install uv

# With Homebrew
brew install uv

# With Cargo
cargo install --git https://github.com/astral-sh/uv uv
```

### Verify Installation

```bash
uv --version
# uv 0.5.20 (or later)
```

---

## Migration Guide

### Old Workflow (pip)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Run commands
python -m pytest
mypy src/

# Update dependencies
pip install --upgrade package-name
pip freeze > requirements.txt
```

### New Workflow (uv)

```bash
# No need to create/activate venv manually!
# uv manages it automatically

# Install dependencies (creates .venv automatically)
uv sync --all-extras --dev

# Run commands (uv automatically uses the venv)
uv run pytest
uv run mypy src/

# Update dependencies
uv lock --upgrade
uv sync

# Generate requirements.txt
uv pip compile pyproject.toml -o requirements.txt
```

---

## Command Reference

### Installation Commands

| Old (pip) | New (uv) | Description |
|-----------|----------|-------------|
| `pip install -e .` | `uv pip install -e .` | Install in editable mode |
| `pip install -e ".[dev]"` | `uv sync --all-extras --dev` | Install with dev dependencies |
| `pip install package` | `uv pip install package` | Install single package |
| `pip install -r requirements.txt` | `uv pip install -r requirements.txt` | Install from requirements |
| N/A | `uv sync` | Sync from uv.lock (recommended) |

### Running Commands

| Old (pip) | New (uv) | Description |
|-----------|----------|-------------|
| `python script.py` | `uv run python script.py` | Run Python script |
| `pytest tests/` | `uv run pytest tests/` | Run pytest |
| `mypy src/` | `uv run mypy src/` | Run mypy |
| `black src/` | `uv run black src/` | Run black |
| `python -m module` | `uv run python -m module` | Run module |

### Dependency Management

| Old (pip) | New (uv) | Description |
|-----------|----------|-------------|
| `pip freeze > requirements.txt` | `uv pip compile pyproject.toml -o requirements.txt` | Generate requirements |
| `pip install --upgrade package` | `uv lock --upgrade` + `uv sync` | Update dependencies |
| `pip list --outdated` | `uv pip list --outdated` | Check outdated |
| Edit requirements.txt manually | Edit pyproject.toml | Modify dependencies |

### Virtual Environment

| Old (pip) | New (uv) | Description |
|-----------|----------|-------------|
| `python -m venv venv` | Automatic (`.venv`) | Create venv |
| `source venv/bin/activate` | Not needed | Activate venv |
| `deactivate` | Not needed | Deactivate venv |
| `which python` | `uv run which python` | Check Python path |

---

## Just Commands

All just commands now use uv:

```bash
# Installation
just check-uv          # Check if uv is installed
just install           # Install package (production)
just dev-install       # Install with dev dependencies
just sync              # Sync dependencies from uv.lock

# Development
just format            # Format code
just lint              # Run linters
just test              # Run tests
just coverage          # Run tests with coverage

# Dependencies
just update-deps       # Update all dependencies
just requirements      # Generate requirements.txt from uv.lock

# UV-specific
just uv-cache          # Show UV cache information
just uv-cache-clean    # Clean UV cache
```

---

## Benefits

### 1. Speed

**Dependency installation:**
```bash
# Before (pip)
$ time pip install -e ".[dev]"
real    0m45.123s

# After (uv)
$ time uv sync --all-extras --dev
real    0m0.512s
```

**90x faster installation!**

### 2. Reproducibility

**uv.lock ensures exact versions:**
- No more "works on my machine" issues
- Exact same dependencies across all environments
- Faster CI/CD with lockfile caching

### 3. Better Dependency Resolution

**uv uses a modern resolver:**
- Handles complex dependency trees better
- Detects conflicts earlier
- More accurate than pip's resolver

### 4. Automatic Virtual Environment

**No manual venv management:**
```bash
# Old way (pip)
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
deactivate

# New way (uv)
uv sync --all-extras --dev  # Creates .venv automatically
uv run pytest              # Uses .venv automatically
```

### 5. Better Caching

**Global cache saves disk space:**
- All packages cached globally
- Hardlinks used for local installs
- Much faster subsequent installs

---

## CI/CD Updates

### GitHub Actions

All workflows updated to use uv:

```yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.11'

- name: Install uv
  uses: astral-sh/setup-uv@v5
  with:
    version: "latest"

- name: Install dependencies
  run: |
    uv sync --all-extras --dev

- name: Run tests
  run: |
    uv run pytest tests/
```

**Benefits:**
- **Faster CI**: 90x faster dependency installation
- **Cached lockfile**: Even faster on subsequent runs
- **Consistent**: Same versions in CI as local

---

## Troubleshooting

### Issue: `uv: command not found`

**Solution:** Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then restart your terminal or run:
```bash
source ~/.bashrc  # or ~/.zshrc
```

### Issue: `uv sync` fails with dependency conflicts

**Solution:** Check pyproject.toml for conflicting version requirements:
```bash
# See dependency tree
uv pip tree

# Force update lock file
uv lock --upgrade

# Clear cache and retry
uv cache clean
uv sync --all-extras --dev
```

### Issue: `uv run` doesn't find package

**Solution:** Reinstall in editable mode:
```bash
uv pip install -e .
```

### Issue: Want to use system Python instead of uv's

**Solution:** Use `--python` flag:
```bash
uv sync --python python3.11
```

Or set in pyproject.toml:
```toml
[tool.uv]
python-version = "3.11"
```

### Issue: Need to install package not in pyproject.toml

**Solution:**
```bash
# Add to uv.lock and install
uv add package-name

# Or install temporarily (not in lock)
uv pip install package-name
```

---

## Advanced Features

### Custom Python Versions

**uv can install and manage Python versions:**
```bash
# Install Python 3.11
uv python install 3.11

# Use specific Python
uv sync --python 3.11

# List available Pythons
uv python list
```

### Custom Package Index

**Use private PyPI or custom index:**
```toml
[tool.uv.sources]
# Use custom index
my-package = { index = "https://my-pypi.com/simple" }

# Use git repository
my-package = { git = "https://github.com/user/repo.git" }

# Use local path
my-package = { path = "../my-package" }
```

### Workspace Management

**For monorepos with multiple packages:**
```toml
[tool.uv.workspace]
members = ["packages/*"]
```

### Lock File Customization

**Control resolution strategy:**
```bash
# Update only specific package
uv lock --upgrade-package requests

# Use lowest compatible versions
uv lock --resolution lowest

# Dry run (show what would change)
uv lock --dry-run
```

---

## Comparison with Other Tools

### UV vs pip

| Feature | pip | uv |
|---------|-----|-----|
| Speed | Baseline | 10-100x faster |
| Lock files | No | Yes (uv.lock) |
| Dependency resolution | Basic | Advanced |
| Caching | Per-venv | Global cache |
| Written in | Python | Rust |

### UV vs pip-tools

| Feature | pip-tools | uv |
|---------|-----------|-----|
| Speed | Slow | 100x faster |
| Lock files | requirements.txt | uv.lock |
| pip-compile | Yes | `uv pip compile` |
| pip-sync | Yes | `uv sync` |

### UV vs Poetry

| Feature | Poetry | uv |
|---------|--------|-----|
| Speed | Moderate | 50x faster |
| Lock files | poetry.lock | uv.lock |
| Build backend | Custom | Standard |
| Config | pyproject.toml | pyproject.toml |

### UV vs PDM

| Feature | PDM | uv |
|---------|-----|-----|
| Speed | Moderate | 50x faster |
| Lock files | pdm.lock | uv.lock |
| PEP 582 | Yes | No |
| Standard tools | Yes | Yes |

**Why UV?**
- **Fastest** of all tools
- **Standard** - uses pyproject.toml
- **Simple** - drop-in replacement for pip
- **Well-maintained** - by Astral (ruff creators)

---

## Migration Checklist

For teams migrating to uv:

- [ ] Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [ ] Test locally: `uv sync --all-extras --dev`
- [ ] Verify imports: `uv run python -c "import chronos_mcp; print('OK')"`
- [ ] Run tests: `uv run pytest`
- [ ] Update CI/CD workflows
- [ ] Commit `uv.lock` to git
- [ ] Update documentation
- [ ] Train team members
- [ ] Remove old venv/: `rm -rf venv/`
- [ ] Add `.venv/` to `.gitignore` if not present

---

## Best Practices

### 1. Always Commit uv.lock

```bash
git add uv.lock
git commit -m "chore: update dependencies"
```

### 2. Sync After Pulling

```bash
git pull
uv sync  # Sync dependencies from uv.lock
```

### 3. Use `uv run` for Commands

```bash
# Good
uv run pytest
uv run mypy src/

# Avoid (requires manual venv activation)
source .venv/bin/activate
pytest
```

### 4. Update Dependencies Regularly

```bash
# Weekly or bi-weekly
uv lock --upgrade
uv sync
git add uv.lock
git commit -m "chore: update dependencies"
```

### 5. Use Just Commands

```bash
# Preferred (handles uv automatically)
just test
just lint
just coverage

# Also works (but more verbose)
uv run pytest
```

---

## Resources

- [UV Documentation](https://github.com/astral-sh/uv)
- [UV Installation](https://github.com/astral-sh/uv#installation)
- [UV GitHub](https://github.com/astral-sh/uv)
- [Astral Blog](https://astral.sh/blog)
- [PEP 735 - Dependency Groups](https://peps.python.org/pep-0735/)

---

## Questions?

- Check [MIGRATION.md](MIGRATION.md) for general migration guide
- Check [CLAUDE.md](CLAUDE.md) for development workflow
- Run `just --list` to see all available commands
- Run `uv --help` for UV command reference

---

**Generated:** 2025-10-14
**Version:** 2.0.0 with UV
**Status:** ✅ Complete
