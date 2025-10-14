#!/usr/bin/env python3
"""
Main entry point for Chronos MCP
"""

from .server import mcp


def main():
    """Entry point for the chronos-mcp command"""
    mcp.run()


if __name__ == "__main__":
    main()
