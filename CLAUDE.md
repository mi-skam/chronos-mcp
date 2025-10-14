# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Core Commands

**IMPORTANT**: This project uses:
- `just` (justfile) for task running - See [justfile](justfile) for all available commands
- `uv` for Python package management - See [UV_MIGRATION.md](UV_MIGRATION.md) for details

### Quick Start

```bash
# Initialize development environment
just init

# Start development server with live-reload
just dev

# Fix linting and formatting issues
just fix

# Quick check before committing
just check
```

### All Commands (14 total)

**SETUP**
```bash
just init          # Initialize from scratch (clean + install + setup)
just install       # Sync dependencies from lock file
just update        # Update all dependencies to latest versions
```

**DEVELOPMENT**
```bash
just dev           # Run server with live-reload (for development)
just serve         # Run server (production mode)
```

**CODE QUALITY**
```bash
just fix           # Auto-fix formatting + linting (runs ruff --fix + format)
just check         # Quick check: lint + types + unit tests (fast!)
just ci            # Full CI/CD: check + coverage + security + complexity
```

**TESTING**
```bash
just test [args]   # Run tests (pass pytest args)
just coverage      # Run tests with coverage report
```

**PUBLISHING**
```bash
just build         # Build distribution packages
just publish       # Publish to PyPI (use --test for TestPyPI)
```

**UTILITIES**
```bash
just clean         # Clean build artifacts (use --deep to include venv)
```

### Common Workflows

```bash
# Daily development
just dev                              # Start dev server

# Fix code issues
just fix                              # Auto-fix all linting/formatting

# Before committing
just check                            # Fast: lint + types + unit tests

# Before pushing
just ci                               # Full: everything including security

# Run specific tests
just test tests/unit/test_events.py   # Single file
just test -k test_create_event        # By name pattern
just test -v                          # Verbose output

# Publishing
just publish --test                   # Test on TestPyPI first
just publish                          # Publish to PyPI

# Deep clean
just clean --deep                     # Remove venv and caches
```

## Architecture Overview

Chronos MCP is a Model Context Protocol server for CalDAV calendar management built with FastMCP 2.0. The codebase follows a **src/ layout** and layered architecture.

### Project Structure

```
chronos-mcp/
├── src/
│   └── chronos_mcp/     # Main package (src layout)
│       ├── server.py    # MCP server entry point
│       ├── accounts.py  # Account management
│       ├── calendars.py # Calendar operations
│       ├── events.py    # Event operations
│       ├── tasks.py     # Task operations
│       ├── journals.py  # Journal operations
│       ├── bulk.py      # Bulk operations
│       ├── search.py    # Search functionality
│       ├── models.py    # Data models
│       ├── validation.py # Input validation
│       └── tools/       # MCP tool definitions
├── tests/               # Test suite
│   └── unit/            # Unit tests
├── justfile             # Task runner (replaces Makefile)
├── pyproject.toml       # Project configuration
└── pytest.ini           # Test configuration
```

### Key Components

1. **MCP Interface Layer** (`src/chronos_mcp/server.py`)
   - Defines MCP tools using FastMCP decorators
   - Handles input validation and error sanitization
   - Maps tool calls to business logic managers

2. **Business Logic Layer**
   - `accounts.py`: Multi-account management with connection caching
   - `calendars.py`: Calendar CRUD operations
   - `events.py`: Event lifecycle including recurring events (RRULE)
   - `tasks.py`: VTODO task management
   - `journals.py`: VJOURNAL journal entry management
   - `bulk.py`: Parallel bulk operations with rollback support
   - `search.py`: Advanced search with relevance ranking

3. **Data Layer**
   - `models.py`: Pydantic models for type safety
   - `config.py`: Account configuration persistence
   - `credentials.py`: Secure password storage via keyring

4. **Validation Layer**
   - `validation.py`: Input sanitization and XSS prevention
   - `rrule.py`: RRULE validation for recurring events
   - `exceptions.py`: Custom exceptions with error sanitization

### Important Patterns

- **Manager Pattern**: Each domain (accounts, calendars, events) has a dedicated manager class
- **Connection Caching**: DAV connections are cached per account to improve performance
- **Error Handling**: All errors are sanitized before returning to prevent information leakage
- **Async Tools**: All MCP tools are async functions decorated with `@mcp.tool`
- **Field Validation**: Pydantic Field() for parameter validation in tool definitions

### Key Files to Understand

- `src/chronos_mcp/server.py`: Entry point and tool definitions - start here to understand available operations
- `src/chronos_mcp/models.py`: Data structures used throughout the codebase
- `src/chronos_mcp/exceptions.py`: Error handling patterns and custom exceptions
- `src/chronos_mcp/validation.py`: Security-critical input validation logic
- `justfile`: Development task runner (replaces Makefile)

### Testing Approach

- Tests are in `tests/unit/` organized by module
- Each manager class has corresponding test file (e.g., `events.py` → `test_events.py`)
- Tests use pytest fixtures defined in `conftest.py`
- Mock CalDAV responses for unit tests to avoid external dependencies

### Security Considerations

- All user input is validated using `InputValidator` class
- Passwords stored securely via system keyring when available
- Path traversal and injection attacks prevented in validation layer
- Error messages sanitized to prevent information disclosure

### Common Development Tasks

When adding new CalDAV functionality:
1. Add Pydantic model to `src/chronos_mcp/models.py` if needed
2. Implement business logic in appropriate manager class under `src/chronos_mcp/`
3. Add tool definition in `src/chronos_mcp/server.py` with proper validation
4. Write unit tests following existing patterns in `tests/unit/`
5. Update API documentation if adding new tools
6. Run `just format` before committing
7. Run `just quick` to verify changes

When fixing bugs:
1. Check if error handling follows the sanitization pattern
2. Ensure input validation is applied consistently
3. Add test case reproducing the bug before fixing
4. Run full test suite to prevent regressions: `just test`
5. Verify with `just ci` before pushing