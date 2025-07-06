"""
Basic usage examples for Chronos MCP
"""

import asyncio
from datetime import datetime, timedelta


async def test_chronos():
    """Test basic Chronos MCP functionality"""
    
    print("Chronos MCP Basic Usage Examples")
    print("=" * 40)
    
    # Note: These are examples of the tools available
    # In actual use, these would be called through the MCP protocol
    
    # Example 1: List accounts
    print("\n1. List configured accounts:")
    print("   Tool: list_accounts()")
    
    # Example 2: Add account
    print("\n2. Add a new account:")
    print("   Tool: add_account(")
    print('       alias="personal",')
    print('       url="https://caldav.example.com",')
    print('       username="user@example.com",')
    print('       password="secret",')
    print('       display_name="Personal Calendar"')
    print("   )")

    
    # Example 3: List calendars
    print("\n3. List calendars:")
    print("   Tool: list_calendars(account='personal')")
    
    # Example 4: Create event
    print("\n4. Create an event:")
    tomorrow = datetime.now() + timedelta(days=1)
    start = tomorrow.replace(hour=14, minute=0)
    end = start + timedelta(hours=1)
    
    print("   Tool: create_event(")
    print('       calendar_uid="work-calendar",')
    print('       summary="Team Meeting",')
    print(f'       start="{start.isoformat()}",')
    print(f'       end="{end.isoformat()}",')
    print('       description="Weekly team sync",')
    print('       location="Conference Room A",')
    print('       alarm_minutes=15')
    print("   )")
    
    # Example 5: Get events
    print("\n5. Get events for next week:")
    week_start = datetime.now()
    week_end = week_start + timedelta(days=7)
    
    print("   Tool: get_events_range(")
    print('       calendar_uid="work-calendar",')
    print(f'       start_date="{week_start.isoformat()}",')
    print(f'       end_date="{week_end.isoformat()}"')
    print("   )")
    
    print("\n" + "=" * 40)
    print("These examples show the available tools in Chronos MCP.")
    print("Use them through your MCP client to manage calendars!")


if __name__ == "__main__":
    asyncio.run(test_chronos())
