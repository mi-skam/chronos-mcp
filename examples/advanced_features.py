"""
Advanced features examples for Chronos MCP v0.1.2
"""

import asyncio
from datetime import datetime, timedelta
import json


async def test_new_features():
    """Test the new features added in v0.1.1 and fixed in v0.1.2"""
    
    print("Chronos MCP v0.1.2 - Advanced Features Examples")
    print("=" * 50)
    
    # Example 1: Create recurring event
    print("\n1. Create a recurring event:")
    print("   Tool: create_event(")
    print('       calendar_uid="work",')
    print('       summary="Weekly Team Meeting",')
    print('       start="2025-07-07T10:00:00",')
    print('       end="2025-07-07T11:00:00",')
    print('       description="Weekly sync with the team",')
    print('       location="Conference Room A",')
    print('       recurrence_rule="FREQ=WEEKLY;BYDAY=MO;COUNT=52",  # Every Monday for a year')
    print('       alarm_minutes="15"  # Note: Now pass as string!')
    print("   )")
    
    # Example 2: Create event with attendees (v0.1.2 format)
    print("\n2. Create event with attendees (JSON format):")
    
    # Prepare attendees list
    attendees = [
        {
            "email": "friend1@example.com",
            "name": "John Doe",
            "role": "REQ-PARTICIPANT",
            "status": "NEEDS-ACTION",
            "rsvp": "true"
        },
        {
            "email": "friend2@example.com",
            "name": "Jane Smith", 
            "role": "OPT-PARTICIPANT",
            "status": "NEEDS-ACTION",
            "rsvp": "true"
        }
    ]
    attendees_json = json.dumps(attendees)
    
    print("   Tool: create_event(")
    print('       calendar_uid="personal",')
    print('       summary="Birthday Party",')
    print('       start="2025-07-15T18:00:00",')
    print('       end="2025-07-15T22:00:00",')
    print('       location="123 Main St",')
    print(f'       attendees_json=\'{attendees_json}\',')
    print('       alarm_minutes="1440"  # 24 hours before')
    print("   )")

    
    # Example 3: Delete an event
    print("\n3. Delete an event:")
    print("   Tool: delete_event(")
    print('       calendar_uid="personal",')
    print('       event_uid="abc123-def456-789",')
    print('       account="personal"')
    print("   )")
    
    # Example 4: Delete a calendar
    print("\n4. Delete a calendar:")
    print("   Tool: delete_calendar(")
    print('       calendar_uid="old-project",')
    print('       account="work"')
    print("   )")
    
    # Example 5: Complex recurring event with attendees
    print("\n5. Complex event - Monthly project review:")
    
    # Prepare complex attendees
    complex_attendees = [
        {"email": "pm@company.com", "name": "Project Manager", "role": "CHAIR"},
        {"email": "dev1@company.com", "name": "Developer 1", "role": "REQ-PARTICIPANT"},
        {"email": "dev2@company.com", "name": "Developer 2", "role": "REQ-PARTICIPANT"},
        {"email": "stakeholder@company.com", "name": "Stakeholder", "role": "OPT-PARTICIPANT"}
    ]
    
    print("   Tool: create_event(")
    print('       calendar_uid="work",')
    print('       summary="Monthly Project Review",')
    print('       start="2025-07-31T14:00:00",')
    print('       end="2025-07-31T16:00:00",')
    print('       description="Review project progress, discuss blockers, plan next sprint",')
    print('       location="https://zoom.us/j/123456789",')
    print('       recurrence_rule="FREQ=MONTHLY;BYDAY=-1FR;COUNT=12",  # Last Friday of each month')
    print('       alarm_minutes="1440",  # Reminder 24 hours before (as string)')
    print(f'       attendees_json=\'{json.dumps(complex_attendees)}\'')
    print("   )")
    
    print("\n" + "=" * 50)
    print("New features in v0.1.2:")
    print("✅ Delete calendar and event operations (fixed)")
    print("✅ Recurring events with RRULE support")
    print("✅ Attendee management (JSON format)")
    print("✅ Alarm/reminder functionality (string format)")
    print("\nParameter format changes in v0.1.2:")
    print("- alarm_minutes: Now pass as string (e.g., '15')")
    print("- attendees: Now use attendees_json with JSON string")
    print("\nRefer to RFC 5545 for RRULE syntax:")
    print("https://tools.ietf.org/html/rfc5545#section-3.8.5.3")


if __name__ == "__main__":
    asyncio.run(test_new_features())
