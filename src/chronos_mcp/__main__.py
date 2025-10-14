#!/usr/bin/env python3
"""
Main entry point for Chronos MCP
"""

from .server import mcp

if __name__ == "__main__":
    mcp.run()
