"""
Chronos MCP Tools - Modular tool definitions
"""

from .accounts import register_account_tools
from .bulk import register_bulk_tools
from .calendars import register_calendar_tools
from .events import register_event_tools
from .journals import register_journal_tools
from .tasks import register_task_tools


__all__ = [
    "register_account_tools",
    "register_bulk_tools",
    "register_calendar_tools",
    "register_event_tools",
    "register_journal_tools",
    "register_task_tools",
]


def register_all_tools(mcp, managers):
    """Register all tool modules with the MCP server"""
    register_account_tools(mcp, managers)
    register_calendar_tools(mcp, managers)
    register_event_tools(mcp, managers)
    register_task_tools(mcp, managers)
    register_journal_tools(mcp, managers)
    register_bulk_tools(mcp, managers)
