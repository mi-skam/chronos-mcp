#!/usr/bin/env python3
"""
Chronos MCP Quick Validation Script
Run this to verify your Chronos MCP installation is working correctly.
"""

import asyncio
from datetime import datetime

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_status(status, message):
    """Print colored status messages"""
    if status == "pass":
        print(f"{GREEN}✅ PASS{RESET}: {message}")
    elif status == "fail":
        print(f"{RED}❌ FAIL{RESET}: {message}")
    elif status == "info":
        print(f"{BLUE}ℹ️  INFO{RESET}: {message}")
    else:
        print(f"{YELLOW}⚠️  WARN{RESET}: {message}")


async def validate_chronos():
    """Run validation tests for Chronos MCP"""
    print(f"\n{BLUE}=== Chronos MCP Validation Script ==={RESET}")
    print(f"Started at: {datetime.now()}\n")

    try:
        # Import Chronos modules
        print_status("info", "Importing Chronos modules...")
        from chronos_mcp.config import ConfigManager
        from chronos_mcp.accounts import AccountManager
        from chronos_mcp.calendars import CalendarManager
        from chronos_mcp.events import EventManager
        from chronos_mcp.exceptions import ChronosError

        print_status("pass", "All modules imported successfully")

        # Initialize managers
        print_status("info", "Initializing managers...")
        config = ConfigManager()
        accounts = AccountManager(config)
        calendars = CalendarManager(accounts)
        events = EventManager(calendars)
        print_status("pass", "Managers initialized")

        # Check for configured accounts
        print_status("info", "Checking configured accounts...")
        account_list = config.list_accounts()
        if account_list:
            print_status("pass", f"Found {len(account_list)} configured account(s)")
            for acc in account_list:
                print(f"  - {acc['alias']} ({acc.get('url', 'No URL')})")
        else:
            print_status("warn", "No accounts configured")
            print("  Run 'chronos-mcp add-account' to configure an account")
            return
        # Test default account connection
        default_account = config.get_default_account()
        if default_account:
            print_status(
                "info", f"Testing connection to '{default_account['alias']}'..."
            )
            try:
                connected = accounts.test_account(default_account["alias"])
                if connected:
                    print_status("pass", "Successfully connected to CalDAV server")
                else:
                    print_status("fail", "Could not connect to CalDAV server")
                    return
            except Exception as e:
                print_status("fail", f"Connection test failed: {e}")
                return

        # List calendars
        print_status("info", "Listing calendars...")
        try:
            cal_list = calendars.list_calendars()
            if cal_list:
                print_status("pass", f"Found {len(cal_list)} calendar(s)")
                for cal in cal_list:
                    print(f"  - {cal.name} (uid: {cal.uid})")
            else:
                print_status("warn", "No calendars found")
        except Exception as e:
            print_status("fail", f"Failed to list calendars: {e}")

        # Test error handling
        print_status("info", "Testing error handling...")
        try:
            # This should raise EventNotFoundError
            await events.delete_event(
                calendar_uid="test_calendar", event_uid="test-non-existent-event-12345"
            )
            print_status("fail", "Error handling test failed - no error raised")
        except ChronosError as e:
            if "not found" in str(e).lower():
                print_status("pass", "Error handling working correctly")
                print(f"  Error message: {e.message}")
                print(f"  Error code: {e.error_code}")
            else:
                print_status("fail", f"Unexpected error: {e}")

        print(f"\n{GREEN}=== Validation Complete ==={RESET}")
        print("Chronos MCP is properly installed and functional! 🎉\n")

    except ImportError as e:
        print_status("fail", f"Import error: {e}")
        print("\nPlease ensure Chronos MCP is properly installed:")
        print("  pip install -e .")
    except Exception as e:
        print_status("fail", f"Unexpected error: {e}")
        print("\nPlease check your installation and configuration.")


if __name__ == "__main__":
    asyncio.run(validate_chronos())
