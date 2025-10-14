# Chronos MCP

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP 2.0+](https://img.shields.io/badge/FastMCP-2.0+-green.svg)](https://github.com/jlowin/fastmcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Model Context Protocol server for CalDAV calendar management. Supports events, tasks (VTODO), and journals (VJOURNAL) with multi-account management and secure credential storage.

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/chronos-mcp.git
cd chronos-mcp

# Initialize development environment
just init
```

## Configuration

### Environment Variables
Add to your shell profile (`.zshrc`, `.bashrc`, etc.):
```bash
export CALDAV_BASE_URL=https://your-caldav-server.com
export CALDAV_USERNAME=your-username
export CALDAV_PASSWORD=your-password
```

### Multi-Account (Optional)
Create `~/.chronos/accounts.json`:
```json
{
  "accounts": {
    "personal": {
      "url": "https://caldav.fastmail.com",
      "username": "user@example.com"
    },
    "work": {
      "url": "https://caldav.company.com",
      "username": "user"
    }
  },
  "default_account": "personal"
}
```

Passwords are stored in system keyring when available (macOS Keychain, Windows Credential Locker, Linux Secret Service).

## Usage

### Connect to Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "chronos": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/chronos-mcp",
        "run",
        "chronos-mcp"
      ],
      "env": {
        "CALDAV_BASE_URL": "https://your-caldav-server.com",
        "CALDAV_USERNAME": "your-username",
        "CALDAV_PASSWORD": "your-password"
      }
    }
  }
}
```

Restart Claude Desktop. The Chronos tools will appear in the MCP tools menu.

**Important for SOGo users:** The CalDAV URL format should be:
```
https://your-server.com/SOGo/dav/your-username/
```

After connecting, create `~/.chronos/accounts.json` to configure your account properly:

```json
{
  "accounts": {
    "default": {
      "url": "https://mail.mxmlab.de/SOGo/dav/maksim@miskam.xyz/",
      "username": "maksim@miskam.xyz",
      "display_name": "SOGo Calendar"
    }
  },
  "default_account": "default"
}
```

Passwords will be stored in your system keyring automatically when you first use the account.

### Example Prompts

Once connected, you can ask Claude:

```
"Create a team meeting event for tomorrow at 2pm"

"Show me all events next week"

"Create a recurring standup every Monday and Friday at 9am"

"Add a task to complete the project documentation by Feb 1st"
```

Claude will use the Chronos MCP tools to interact with your CalDAV server.

### Development

```bash
# Start development server with live-reload
just dev

# Run tests
just test

# Run full CI checks (lint, types, tests, security, complexity)
just ci

# Format code
just fix
```

## References

- [API Reference](docs/api/README.md)
- [Architecture Guide](docs/ARCHITECTURE.md)
- [RRULE Guide](docs/RRULE_GUIDE.md)
- [VTODO/VJOURNAL Guide](docs/VTODO_VJOURNAL_GUIDE.md)
- [Known Issues](KNOWN_ISSUES.md)
- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
