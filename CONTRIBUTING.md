# Contributing to Chronos MCP

First off, thank you for considering contributing to Chronos MCP! It's people like you that make Chronos MCP such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by the [Chronos MCP Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible using our [bug report template](.github/ISSUE_TEMPLATE/bug_report.md).

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. Create an issue using our [feature request template](.github/ISSUE_TEMPLATE/feature_request.md) and provide the following information:

* Use a clear and descriptive title
* Provide a step-by-step description of the suggested enhancement
* Provide specific examples to demonstrate the steps
* Describe the current behavior and explain which behavior you expected to see instead
* Explain why this enhancement would be useful

### Your First Code Contribution

Unsure where to begin contributing? You can start by looking through these `beginner` and `help-wanted` issues:

* [Beginner issues](https://github.com/chronos-mcp/chronos-mcp/labels/beginner) - issues which should only require a few lines of code
* [Help wanted issues](https://github.com/chronos-mcp/chronos-mcp/labels/help%20wanted) - issues which should be a bit more involved

### Development Setup

1. Fork the repo and create your branch from `main`:
   ```bash
   git clone https://github.com/your-username/chronos-mcp.git
   cd chronos-mcp
   git checkout -b feature/your-feature-name
   ```

2. Install dependencies using just:
   ```bash
   just init
   ```

   Or manually with uv:
   ```bash
   uv sync --all-extras --dev
   ```

3. Create a test CalDAV server (we recommend Radicale):
   ```bash
   uv pip install radicale
   uv run python -m radicale --config tests/fixtures/radicale.conf
   ```

### Pull Request Process

1. Ensure any install or build dependencies are removed before the end of the layer when doing a build.
2. Update the README.md with details of changes to the interface, including new environment variables, exposed ports, useful file locations, and container parameters.
3. Increase the version numbers in any examples files and the README.md to the new version that this Pull Request would represent. The versioning scheme we use is [SemVer](http://semver.org/).
4. You may merge the Pull Request once you have the sign-off of two other developers, or if you do not have permission to do that, you may request the second reviewer to merge it for you.

### Coding Standards

* We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting
* We use [mypy](http://mypy-lang.org/) for type checking
* All code must pass CI checks before merging

Run all checks with:
```bash
just fix      # Auto-fix formatting and linting issues
just check    # Quick check: lint + types + unit tests
just ci       # Full CI/CD checks: everything including coverage and security
just test     # Run all tests
```

### Testing

* Write unit tests for all new functionality
* Ensure all tests pass before submitting PR
* Aim for >80% code coverage
* Test with multiple Python versions (3.9, 3.10, 3.11, 3.12)

### Documentation

* Use clear, descriptive variable names
* Add docstrings to all functions and classes
* Update README.md if adding new features
* Add inline comments for complex logic

### Commit Messages

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

* `feat:` New feature
* `fix:` Bug fix
* `docs:` Documentation changes
* `style:` Code style changes (formatting, missing semi-colons, etc)
* `refactor:` Code refactoring
* `perf:` Performance improvements
* `test:` Adding or updating tests
* `chore:` Maintenance tasks

Example:
```
feat: add support for recurring events

- Implement RRULE parsing
- Add recurrence UI in event creation
- Update event model to handle recurrence

Closes #123
```

### Security

* Never commit credentials or API keys
* Always sanitize error messages shown to users
* Validate all user inputs
* Follow OWASP guidelines for web security
* Report security vulnerabilities to security@chronos-mcp.org

## Questions?

Feel free to open an issue with the `question` label or reach out in our [Discord community](https://discord.gg/chronos-mcp).

Thank you for contributing! 🎉
