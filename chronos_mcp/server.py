"""
Chronos MCP Server - Advanced CalDAV Management
"""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union

from fastmcp import FastMCP
from pydantic import BaseModel, Field

from .logging_config import setup_logging
from .config import ConfigManager
from .accounts import AccountManager  
from .calendars import CalendarManager
from .events import EventManager
from .tasks import TaskManager
from .journals import JournalManager
from .models import Account, Calendar, Event, Task, Journal
from .search import SearchOptions, search_events as search_events_func, search_events_ranked
from .rrule import RRuleValidator, RRuleTemplates
from .validation import InputValidator
from .bulk import BulkOperationManager, BulkOptions, BulkOperationMode
from .exceptions import (
    ChronosError,
    ErrorSanitizer,
    AccountAlreadyExistsError,
    AccountNotFoundError,
    CalendarNotFoundError,
    EventNotFoundError,
    EventCreationError,
    DateTimeValidationError,
    AttendeeValidationError,
    ValidationError
)

# Set up logging
logger = setup_logging()

# Initialize FastMCP server
mcp = FastMCP("chronos-mcp")

# Log startup
logger.info("Initializing Chronos MCP Server...")

# Initialize managers
try:
    config_manager = ConfigManager()
    account_manager = AccountManager(config_manager)
    calendar_manager = CalendarManager(account_manager)
    event_manager = EventManager(calendar_manager)
    task_manager = TaskManager(calendar_manager)
    journal_manager = JournalManager(calendar_manager)
    bulk_manager = BulkOperationManager(
        event_manager=event_manager,
        task_manager=task_manager,
        journal_manager=journal_manager
    )
    logger.info("All managers initialized successfully")
except Exception as e:
    logger.error(f"Error initializing managers: {e}")
    raise


# ============= Account Management Tools =============

@mcp.tool
async def add_account(
    alias: str = Field(..., description="Unique alias for the account"),
    url: str = Field(..., description="CalDAV server URL"),
    username: str = Field(..., description="Username for authentication"),
    password: str = Field(..., description="Password for authentication"),
    display_name: Optional[str] = Field(None, description="Display name for the account")
) -> Dict[str, Any]:
    """Add a new CalDAV account to Chronos"""
    request_id = str(uuid.uuid4())
    
    try:
        account = Account(
            alias=alias,
            url=url,
            username=username,
            password=password,
            display_name=display_name or alias
        )
        config_manager.add_account(account)
        
        # Test connection
        test_result = account_manager.test_account(alias, request_id=request_id)
        
        return {
            "success": True,
            "alias": alias,
            "connected": test_result["connected"],
            "calendars": test_result["calendars"],
            "message": f"Account '{alias}' added successfully",
            "request_id": request_id
        }
        
    except AccountAlreadyExistsError as e:
        e.request_id = request_id
        logger.error(f"Account already exists: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Add account failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Failed to add account: {str(e)}",
            details={
                "tool": "add_account",
                "alias": alias,
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error adding account: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


@mcp.tool
async def list_accounts() -> Dict[str, Any]:
    """List all configured CalDAV accounts"""
    accounts = config_manager.list_accounts()
    
    return {
        "accounts": [
            {
                "alias": alias,
                "url": str(acc.url),
                "display_name": acc.display_name,
                "status": acc.status,
                "is_default": alias == config_manager.config.default_account
            }
            for alias, acc in accounts.items()
        ],
        "total": len(accounts)
    }


@mcp.tool
async def remove_account(
    alias: str = Field(..., description="Account alias to remove")
) -> Dict[str, Any]:
    """Remove a CalDAV account from Chronos"""
    request_id = str(uuid.uuid4())
    
    try:
        # Check if account exists
        if not config_manager.get_account(alias):
            raise AccountNotFoundError(alias, request_id=request_id)
            
        account_manager.disconnect_account(alias)
        config_manager.remove_account(alias)
        
        return {
            "success": True,
            "message": f"Account '{alias}' removed successfully",
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Remove account failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Failed to remove account: {str(e)}",
            details={
                "tool": "remove_account",
                "alias": alias,
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error removing account: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


@mcp.tool
async def test_account(
    alias: str = Field(..., description="Account alias to test")
) -> Dict[str, Any]:
    """Test connectivity to a CalDAV account"""
    return account_manager.test_account(alias)


# ============= Calendar Management Tools =============

@mcp.tool
async def list_calendars(
    account: Optional[str] = Field(None, description="Account alias (uses default if not specified)")
) -> Dict[str, Any]:
    """List all calendars for an account"""
    calendars = calendar_manager.list_calendars(account)
    
    return {
        "calendars": [
            {
                "uid": cal.uid,
                "name": cal.name,
                "description": cal.description,
                "color": cal.color,
                "url": cal.url,
                "account": cal.account_alias
            }
            for cal in calendars
        ],
        "total": len(calendars),
        "account": account or config_manager.config.default_account
    }


@mcp.tool
async def create_calendar(
    name: str = Field(..., description="Calendar name"),
    description: Optional[str] = Field(None, description="Calendar description"),
    color: Optional[str] = Field(None, description="Calendar color (hex format)"),
    account: Optional[str] = Field(None, description="Account alias (uses default if not specified)")
) -> Dict[str, Any]:
    """Create a new calendar"""
    calendar = calendar_manager.create_calendar(name, description, color, account)
    
    if calendar:
        return {
            "success": True,
            "calendar": {
                "uid": calendar.uid,
                "name": calendar.name,
                "url": calendar.url
            }
        }
    else:
        return {
            "success": False,
            "error": "Failed to create calendar"
        }


@mcp.tool
async def delete_calendar(
    calendar_uid: str = Field(..., description="Calendar UID to delete"),
    account: Optional[str] = Field(None, description="Account alias (uses default if not specified)")
) -> Dict[str, Any]:
    """Delete a calendar"""
    request_id = str(uuid.uuid4())
    
    try:
        calendar_manager.delete_calendar(calendar_uid, account, request_id=request_id)
        
        return {
            "success": True,
            "message": f"Calendar '{calendar_uid}' deleted successfully",
            "request_id": request_id
        }
            
    except CalendarNotFoundError as e:
        e.request_id = request_id
        logger.error(f"Calendar not found for deletion: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Delete calendar failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Failed to delete calendar: {str(e)}",
            details={
                "tool": "delete_calendar",
                "calendar_uid": calendar_uid,
                "account": account,
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error deleting calendar: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


# ============= Event Management Tools =============

@mcp.tool
async def create_event(
    calendar_uid: str = Field(..., description="Calendar UID"),
    summary: str = Field(..., description="Event title/summary"),
    start: str = Field(..., description="Event start time (ISO format)"),
    end: str = Field(..., description="Event end time (ISO format)"),
    description: Optional[str] = Field(None, description="Event description"),
    location: Optional[str] = Field(None, description="Event location"),
    all_day: bool = Field(False, description="Whether this is an all-day event"),
    alarm_minutes: Optional[str] = Field(None, description="Reminder minutes before event as string ('-10080' to '10080')"),
    recurrence_rule: Optional[str] = Field(None, description="RRULE for recurring events (e.g., 'FREQ=WEEKLY;BYDAY=MO')"),
    attendees_json: Optional[str] = Field(None, description="JSON string of attendees list [{email, name, role, status, rsvp}]"),
    related_to: Optional[List[str]] = Field(None, description="List of related component UIDs"),
    account: Optional[str] = Field(None, description="Account alias")
) -> Dict[str, Any]:
    """Create a new calendar event"""
    from .utils import parse_datetime
    from .validation import InputValidator, ValidationError
    import json
    
    request_id = str(uuid.uuid4())
    
    try:
        # Validate and sanitize text inputs
        try:
            summary = InputValidator.validate_text_field(summary, 'summary', required=True)
            if description:
                description = InputValidator.validate_text_field(description, 'description')
            if location:
                location = InputValidator.validate_text_field(location, 'location')
        except ValidationError as e:
            return {
                "success": False,
                "error": str(e),
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id
            }
        
        # Validate alarm_minutes range
        alarm_mins = None
        if alarm_minutes is not None:
            try:
                alarm_mins = int(alarm_minutes)
                if not -10080 <= alarm_mins <= 10080:  # ±1 week
                    return {
                        "success": False,
                        "error": "alarm_minutes must be between -10080 and 10080 (±1 week)",
                        "error_code": "VALIDATION_ERROR",
                        "request_id": request_id
                    }
            except ValueError:
                return {
                    "success": False,
                    "error": "alarm_minutes must be a valid integer string",
                    "error_code": "VALIDATION_ERROR",
                    "request_id": request_id
                }
        start_dt = parse_datetime(start)
        end_dt = parse_datetime(end)
        
        # Parse attendees from JSON
        attendees_list = None
        if attendees_json:
            try:
                attendees_list = json.loads(attendees_json)
                # Validate attendees
                attendees_list = InputValidator.validate_attendees(attendees_list)
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Invalid JSON format for attendees",
                    "error_code": "VALIDATION_ERROR",
                    "request_id": request_id
                }
            except ValidationError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "error_code": "VALIDATION_ERROR", 
                    "request_id": request_id
                }
        
        event = event_manager.create_event(
            calendar_uid=calendar_uid,
            summary=summary,
            start=start_dt,
            end=end_dt,
            description=description,
            location=location,
            all_day=all_day,
            alarm_minutes=alarm_mins,
            recurrence_rule=recurrence_rule,
            attendees=attendees_list,
            related_to=related_to,
            account_alias=account
        )
        
        return {
            "success": True,
            "event": {
                "uid": event.uid,
                "summary": event.summary,
                "start": event.start.isoformat(),
                "end": event.end.isoformat()
            }
        }
            
    except DateTimeValidationError as e:
        e.request_id = request_id
        logger.error(f"Invalid datetime in create_event: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except AttendeeValidationError as e:
        e.request_id = request_id
        logger.error(f"Invalid attendee data in create_event: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except EventCreationError as e:
        e.request_id = request_id
        logger.error(f"Event creation error: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Create event failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Failed to create event: {str(e)}",
            details={
                "tool": "create_event",
                "summary": summary,
                "calendar_uid": calendar_uid,
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in create_event: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


@mcp.tool  
async def get_events_range(
    calendar_uid: str = Field(..., description="Calendar UID"),
    start_date: str = Field(..., description="Start date (ISO format)"),
    end_date: str = Field(..., description="End date (ISO format)"),
    account: Optional[str] = Field(None, description="Account alias")
) -> Dict[str, Any]:
    """Get events within a date range"""
    from .utils import parse_datetime
    
    request_id = str(uuid.uuid4())
    
    try:
        start_dt = parse_datetime(start_date)
        end_dt = parse_datetime(end_date)
        
        events = event_manager.get_events_range(
            calendar_uid=calendar_uid,
            start_date=start_dt,
            end_date=end_dt,
            account_alias=account
        )
        
        return {
            "events": [
                {
                    "uid": event.uid,
                    "summary": event.summary,
                    "description": event.description,
                    "start": event.start.isoformat(),
                    "end": event.end.isoformat(),
                    "location": event.location,
                    "all_day": event.all_day
                }
                for event in events
            ],
            "total": len(events),
            "range": {
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat()
            }
        }
    except DateTimeValidationError as e:
        e.request_id = request_id
        logger.error(f"Invalid date format in get_events_range: {e}")
        
        return {
            "events": [],
            "total": 0,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except CalendarNotFoundError as e:
        e.request_id = request_id
        logger.error(f"Calendar not found in get_events_range: {e}")
        
        return {
            "events": [],
            "total": 0,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Get events range failed: {e}")
        
        return {
            "events": [],
            "total": 0,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Failed to retrieve events: {str(e)}",
            details={
                "tool": "get_events_range",
                "calendar_uid": calendar_uid,
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in get_events_range: {chronos_error}")
        
        return {
            "events": [],
            "total": 0,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


@mcp.tool
async def delete_event(
    calendar_uid: str = Field(..., description="Calendar UID"),
    event_uid: str = Field(..., description="Event UID to delete"),
    account: Optional[str] = Field(None, description="Account alias")
) -> Dict[str, Any]:
    """Delete a calendar event"""
    request_id = str(uuid.uuid4())
    
    try:
        event_manager.delete_event(
            calendar_uid=calendar_uid,
            event_uid=event_uid,
            account_alias=account,
            request_id=request_id
        )
        
        return {
            "success": True,
            "message": f"Event '{event_uid}' deleted successfully",
            "request_id": request_id
        }
            
    except EventNotFoundError as e:
        e.request_id = request_id
        logger.error(f"Event not found for deletion: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except CalendarNotFoundError as e:
        e.request_id = request_id
        logger.error(f"Calendar not found for event deletion: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Delete event failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Failed to delete event: {str(e)}",
            details={
                "tool": "delete_event",
                "event_uid": event_uid,
                "calendar_uid": calendar_uid,
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in delete_event: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }



# ============= Main Entry Point =============
# (moved to end of file)

@mcp.tool
async def update_event(
    calendar_uid: str = Field(..., description="Calendar UID"),
    event_uid: str = Field(..., description="Event UID to update"),
    summary: Optional[str] = Field(None, description="Event title/summary"),
    start: Optional[str] = Field(None, description="Event start time (ISO format)"),
    end: Optional[str] = Field(None, description="Event end time (ISO format)"),
    description: Optional[str] = Field(None, description="Event description"),
    location: Optional[str] = Field(None, description="Event location"),
    all_day: Optional[bool] = Field(None, description="Whether this is an all-day event"),
    alarm_minutes: Optional[str] = Field(None, description="Reminder minutes before event as string ('-10080' to '10080')"),
    recurrence_rule: Optional[str] = Field(None, description="RRULE for recurring events"),
    attendees_json: Optional[str] = Field(None, description="JSON string of attendees list"),
    account: Optional[str] = Field(None, description="Account alias")
) -> Dict[str, Any]:
    """Update an existing calendar event. Only provided fields will be updated."""
    from .utils import parse_datetime
    from .validation import InputValidator, ValidationError
    import json
    
    request_id = str(uuid.uuid4())
    
    try:
        # Validate and sanitize text inputs if provided
        try:
            if summary is not None:
                summary = InputValidator.validate_text_field(summary, 'summary', required=True)
            if description is not None:
                description = InputValidator.validate_text_field(description, 'description')
            if location is not None:
                location = InputValidator.validate_text_field(location, 'location')
        except ValidationError as e:
            return {
                "success": False,
                "error": str(e),
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id
            }
        
        # Validate alarm_minutes range if provided
        alarm_mins = None
        if alarm_minutes is not None:
            try:
                alarm_mins = int(alarm_minutes)
                if not -10080 <= alarm_mins <= 10080:  # ±1 week
                    return {
                        "success": False,
                        "error": "alarm_minutes must be between -10080 and 10080 (±1 week)",
                        "error_code": "VALIDATION_ERROR",
                        "request_id": request_id
                    }
            except ValueError:
                return {
                    "success": False,
                    "error": "alarm_minutes must be a valid integer string",
                    "error_code": "VALIDATION_ERROR",
                    "request_id": request_id
                }
        
        # Parse datetime fields if provided
        start_dt = parse_datetime(start) if start else None
        end_dt = parse_datetime(end) if end else None
        
        # Parse attendees JSON if provided
        attendees = None
        if attendees_json:
            try:
                attendees = json.loads(attendees_json)
                if not isinstance(attendees, list):
                    raise ValueError("Attendees must be a list")
                # Validate attendees
                attendees = InputValidator.validate_attendees(attendees)
            except (json.JSONDecodeError, ValueError) as e:
                return {
                    "success": False,
                    "error": f"Invalid attendees format: {str(e)}",
                    "error_code": "VALIDATION_ERROR",
                    "request_id": request_id
                }
            except ValidationError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "error_code": "VALIDATION_ERROR",
                    "request_id": request_id
                }
        
        # Update the event
        updated_event = event_manager.update_event(
            calendar_uid=calendar_uid,
            event_uid=event_uid,
            summary=summary,
            description=description,
            start=start_dt,
            end=end_dt,
            location=location,
            all_day=all_day,
            attendees=attendees,
            alarm_minutes=alarm_mins,
            recurrence_rule=recurrence_rule,
            account_alias=account,
            request_id=request_id
        )
        
        # Format response
        event_data = {
            "uid": updated_event.uid,
            "summary": updated_event.summary,
            "start": updated_event.start.isoformat() if updated_event.start else None,
            "end": updated_event.end.isoformat() if updated_event.end else None,
            "all_day": updated_event.all_day,
            "description": updated_event.description,
            "location": updated_event.location,
            "recurrence_rule": updated_event.recurrence_rule,
            "attendees": [
                {
                    "email": att.email,
                    "name": att.name,
                    "role": att.role,
                    "status": att.status,
                    "rsvp": att.rsvp
                }
                for att in updated_event.attendees
            ] if updated_event.attendees else [],
            "alarms": [
                {
                    "action": alarm.action,
                    "trigger": alarm.trigger,
                    "description": alarm.description
                }
                for alarm in updated_event.alarms
            ] if updated_event.alarms else []
        }
        
        return {
            "success": True,
            "event": event_data,
            "message": f"Event '{event_uid}' updated successfully",
            "request_id": request_id
        }
        
    except EventNotFoundError as e:
        e.request_id = request_id
        logger.error(f"Event not found for update: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except (CalendarNotFoundError, EventCreationError) as e:
        e.request_id = request_id
        logger.error(f"Update event failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Update event failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Failed to update event: {str(e)}",
            details={
                "tool": "update_event",
                "event_uid": event_uid,
                "calendar_uid": calendar_uid,
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in update_event: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }



# ============= Recurring Event Management Tools =============

@mcp.tool
async def create_recurring_event(
    calendar_uid: str = Field(..., description="Calendar UID"),
    summary: str = Field(..., description="Event title/summary"),
    start: str = Field(..., description="Event start time (ISO format)"),
    duration_minutes: Union[int, str] = Field(..., description="Event duration in minutes"),
    recurrence_rule: str = Field(..., description="RRULE for recurring events (e.g., 'FREQ=WEEKLY;BYDAY=MO,WE,FR;COUNT=10')"),
    description: Optional[str] = Field(None, description="Event description"),
    location: Optional[str] = Field(None, description="Event location"),
    alarm_minutes: Optional[str] = Field(None, description="Reminder minutes before event as string ('-10080' to '10080')"),
    attendees_json: Optional[str] = Field(None, description="JSON string of attendees list"),
    account: Optional[str] = Field(None, description="Account alias")
) -> Dict[str, Any]:
    """
    Create a recurring event with validation.
    
    The recurrence_rule must be a valid RRULE string that includes either
    COUNT or UNTIL to prevent infinite recurrence.
    
    Examples:
    - Daily standup for 2 weeks: "FREQ=DAILY;COUNT=10;BYDAY=MO,TU,WE,TH,FR"
    - Weekly meeting: "FREQ=WEEKLY;BYDAY=TU;UNTIL=20250630T000000Z"
    - Monthly report: "FREQ=MONTHLY;BYMONTHDAY=15;COUNT=12"
    """
    from .utils import parse_datetime
    import json
    
    request_id = str(uuid.uuid4())
    
    # Handle type conversion for parameters that might come as strings from MCP
    if duration_minutes is not None:
        try:
            duration_minutes = int(duration_minutes)
        except (ValueError, TypeError):
            return {
                "success": False,
                "error": f"Invalid duration_minutes value: {duration_minutes}. Must be an integer",
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id
            }
    
    try:
        # Validate RRULE first
        is_valid, error_msg = RRuleValidator.validate_rrule(recurrence_rule)
        if not is_valid:
            return {
                "success": False,
                "error": f"Invalid recurrence rule: {error_msg}",
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id
            }
            
        # Validate and sanitize text inputs
        try:
            summary = InputValidator.validate_text_field(summary, 'summary', required=True)
            if description:
                description = InputValidator.validate_text_field(description, 'description')
            if location:
                location = InputValidator.validate_text_field(location, 'location')
        except ValidationError as e:
            return {
                "success": False,
                "error": str(e),
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id
            }
            
        # Parse start time and calculate end time
        start_dt = parse_datetime(start)
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        
        # Validate alarm_minutes range if provided
        alarm_mins = None
        if alarm_minutes is not None:
            try:
                alarm_mins = int(alarm_minutes)
                if not -10080 <= alarm_mins <= 10080:  # ±1 week
                    return {
                        "success": False,
                        "error": "alarm_minutes must be between -10080 and 10080 (±1 week)",
                        "error_code": "VALIDATION_ERROR",
                        "request_id": request_id
                    }
            except ValueError:
                return {
                    "success": False,
                    "error": "alarm_minutes must be a valid integer string",
                    "error_code": "VALIDATION_ERROR",
                    "request_id": request_id
                }
                
        # Parse attendees from JSON if provided
        attendees_list = None
        if attendees_json:
            try:
                attendees_list = json.loads(attendees_json)
                attendees_list = InputValidator.validate_attendees(attendees_list)
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Invalid JSON format for attendees",
                    "error_code": "VALIDATION_ERROR",
                    "request_id": request_id
                }
            except ValidationError as e:
                return {
                    "success": False,
                    "error": str(e),
                    "error_code": "VALIDATION_ERROR",
                    "request_id": request_id
                }
                
        # Create the recurring event
        event = event_manager.create_event(
            calendar_uid=calendar_uid,
            summary=summary,
            start=start_dt,
            end=end_dt,
            description=description,
            location=location,
            all_day=False,  # Recurring events with duration can't be all-day
            alarm_minutes=alarm_mins,
            recurrence_rule=recurrence_rule,
            attendees=attendees_list,
            account_alias=account,
            request_id=request_id
        )
        
        # Get RRULE info for response
        rrule_info = RRuleValidator.get_rrule_info(recurrence_rule)
        
        return {
            "success": True,
            "event": {
                "uid": event.uid,
                "summary": event.summary,
                "start": event.start.isoformat(),
                "end": event.end.isoformat()
            },
            "recurrence_info": rrule_info,
            "message": f"Recurring event '{summary}' created successfully",
            "request_id": request_id
        }
        
    except (AccountNotFoundError, CalendarNotFoundError, EventCreationError) as e:
        e.request_id = request_id
        logger.error(f"Recurring event creation failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Recurring event creation failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Failed to create recurring event: {str(e)}",
            details={
                "tool": "create_recurring_event",
                "calendar_uid": calendar_uid,
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in create_recurring_event: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


# ============= Search and Advanced Features =============

@mcp.tool
async def search_events(
    query: str = Field(..., description="Search query string"),
    fields: Optional[List[str]] = Field(None, description="Fields to search in (default: summary, description, location)"),
    case_sensitive: bool = Field(False, description="Case-sensitive search"),
    date_start: Optional[str] = Field(None, description="Start date for range filter (ISO format)"),
    date_end: Optional[str] = Field(None, description="End date for range filter (ISO format)"),
    calendar_uid: Optional[str] = Field(None, description="Specific calendar to search (searches all if not specified)"),
    max_results: Optional[Union[int, str]] = Field(50, description="Maximum number of results to return"),
    account: Optional[str] = Field(None, description="Account alias (uses default if not specified)")
) -> Dict[str, Any]:
    """
    Search for events with simple text matching.
    No regex, no complexity, just finding your stuff.
    """
    request_id = str(uuid.uuid4())
    
    # Handle type conversion for parameters that might come as strings from MCP
    if max_results is not None:
        try:
            max_results = int(max_results)
        except (ValueError, TypeError):
            return {
                "success": False,
                "error": f"Invalid max_results value: {max_results}. Must be an integer",
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id
            }
    
    try:
        # Input validation
        if len(query) > 1000:
            raise ValueError("Search query too long (max 1000 chars)")
        if len(query) < 2:
            raise ValueError("Search query too short (min 2 chars)")
            
        # Default fields
        if fields is None:
            fields = ['summary', 'description', 'location']
        
        # Validate fields (prevent prototype pollution)
        allowed_fields = {'summary', 'description', 'location', 'uid', 'dtstart', 'dtend'}
        for field in fields:
            if field not in allowed_fields:
                raise ValueError(f"Invalid field: {field}")
        
        # Get events from range - need datetime objects, not strings!
        from .utils import parse_datetime
        if date_start:
            start_dt = parse_datetime(date_start)
        else:
            start_dt = datetime.now()
            
        if date_end:
            end_dt = parse_datetime(date_end)
        else:
            end_dt = datetime.now() + timedelta(days=365)
        
        # Get all calendars or specific one
        if calendar_uid:
            calendars = [calendar_uid]
        else:
            cal_list = calendar_manager.list_calendars(account)
            calendars = [cal.uid for cal in cal_list]
        
        all_matches = []
        query_lower = query.lower() if not case_sensitive else query
        
        for cal_uid in calendars:
            try:
                # Use event_manager directly (no await)
                events = event_manager.get_events_range(
                    calendar_uid=cal_uid,
                    start_date=start_dt,
                    end_date=end_dt,
                    account_alias=account,
                    request_id=request_id
                )
                
                # Simple substring search
                for event in events:
                    # Events are Event model objects, not dicts
                    for field in fields:
                        # Map field names to actual event properties
                        field_map = {'dtstart': 'start', 'dtend': 'end'}
                        actual_field = field_map.get(field, field)
                        
                        # Use getattr for model objects
                        value = getattr(event, actual_field, '')
                        if value is None:
                            value = ''
                        check_value = str(value).lower() if not case_sensitive else str(value)
                        
                        if query_lower in check_value:
                            all_matches.append({
                                'calendar_uid': cal_uid,
                                'uid': event.uid,
                                'summary': event.summary,
                                'start': event.start.isoformat() if hasattr(event.start, 'isoformat') else str(event.start),
                                'matched_field': field,
                                'preview': str(value)[:100]
                            })
                            break
                            
                    if len(all_matches) >= max_results:
                        break
                        
            except Exception as e:
                # Log but continue with other calendars
                logger.warning(f"Error searching calendar {cal_uid}: {e}")
                
        return {
            'success': True,
            'query': query,
            'matches': all_matches[:max_results],
            'total': len(all_matches),
            'truncated': len(all_matches) > max_results,
            'request_id': request_id
        }
        
    except ValidationError as e:
        return {
            "success": False,
            "error": str(e),
            "error_code": "VALIDATION_ERROR",
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Search failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Search failed: {str(e)}",
            details={
                "tool": "search_events",
                "query": query,
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in search_events: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


@mcp.tool
async def bulk_create_events(
    calendar_uid: str = Field(..., description="Calendar UID to create events in"),
    events: List[Dict[str, Any]] = Field(..., description="List of event data dictionaries"),
    mode: str = Field("continue", description="Operation mode: continue or fail_fast"),
    validate_before_execute: bool = Field(True, description="Validate all events before execution"),
    account: Optional[str] = Field(None, description="Account alias (uses default if not specified)")
) -> Dict[str, Any]:
    """
    Create multiple events. Returns detailed success/failure info.
    No lies about atomic operations - just honest results.
    
    Modes:
    - continue: Process all events, report individual failures
    - fail_fast: Stop on first error
    
    Each event dict should contain: summary, dtstart, dtend, and optional fields
    like description, location, attendees_json, recurrence_rule, etc.
    """
    request_id = str(uuid.uuid4())
    
    try:
        # Validate mode
        if mode not in ["continue", "fail_fast"]:
            raise ValueError(f"Invalid mode '{mode}'. Must be one of: continue, fail_fast")
        
        # Validate first if requested
        if validate_before_execute:
            for i, event in enumerate(events):
                if 'summary' not in event:
                    raise ValueError(f"Event {i} missing required 'summary' field")
                if 'dtstart' not in event or 'dtend' not in event:
                    raise ValueError(f"Event {i} missing required date fields")
        
        # Process events
        results = {
            'total': len(events),
            'succeeded': 0,
            'failed': 0,
            'details': []
        }
        
        for i, event_data in enumerate(events):
            try:
                # Parse datetime fields
                from .utils import parse_datetime
                start_dt = parse_datetime(event_data['dtstart'])
                end_dt = parse_datetime(event_data['dtend'])
                
                # Parse alarm if provided
                alarm_mins = None
                if 'alarm_minutes' in event_data and event_data['alarm_minutes'] is not None:
                    try:
                        alarm_mins = int(event_data['alarm_minutes'])
                        # Validate range
                        if not -10080 <= alarm_mins <= 10080:
                            raise ValueError(f"alarm_minutes must be between -10080 and 10080, got {alarm_mins}")
                    except (ValueError, TypeError) as e:
                        raise ValueError(f"Invalid alarm_minutes in event {i}: {e}")
                
                # Parse attendees if provided
                attendees = None
                if 'attendees_json' in event_data and event_data['attendees_json']:
                    try:
                        from .validation import InputValidator
                        attendees = json.loads(event_data['attendees_json'])
                        if not isinstance(attendees, list):
                            raise ValueError("Attendees must be a list")
                        # Validate attendees
                        attendees = InputValidator.validate_attendees(attendees)
                    except (json.JSONDecodeError, ValueError) as e:
                        raise ValueError(f"Invalid attendees in event {i}: {e}")
                
                # Validate text fields
                from .validation import InputValidator, ValidationError
                try:
                    summary = InputValidator.validate_text_field(
                        event_data['summary'], 'summary', required=True
                    )
                    description = InputValidator.validate_text_field(
                        event_data.get('description', ''), 'description'
                    ) if event_data.get('description') else None
                    location = InputValidator.validate_text_field(
                        event_data.get('location', ''), 'location'
                    ) if event_data.get('location') else None
                except ValidationError as e:
                    raise ValueError(f"Validation error in event {i}: {e}")
                
                # Create event using event_manager directly (no await)
                created = event_manager.create_event(
                    calendar_uid=calendar_uid,
                    summary=summary,  # Use validated summary
                    start=start_dt,
                    end=end_dt,
                    description=description,  # Use validated description
                    location=location,  # Use validated location
                    all_day=event_data.get('all_day', False),
                    attendees=attendees,
                    recurrence_rule=event_data.get('recurrence_rule'),
                    alarm_minutes=alarm_mins,
                    account_alias=account,
                    request_id=request_id
                )
                
                results['succeeded'] += 1
                results['details'].append({
                    'index': i,
                    'success': True,
                    'uid': created.uid if hasattr(created, 'uid') else created.get('uid', 'unknown'),
                    'summary': event_data['summary']
                })
                
            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'index': i,
                    'success': False,
                    'error': str(e),
                    'summary': event_data.get('summary', 'Unknown')
                })
                
                if mode == "fail_fast":
                    break
        
        results['success'] = results['failed'] == 0
        results['request_id'] = request_id
        return results
        
    except ValidationError as e:
        return {
            "success": False,
            "error": str(e),
            "error_code": "VALIDATION_ERROR",
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Bulk create failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Bulk create failed: {str(e)}",
            details={
                "tool": "bulk_create_events",
                "calendar_uid": calendar_uid,
                "event_count": len(events),
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in bulk_create_events: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


@mcp.tool
async def bulk_delete_events(
    calendar_uid: str = Field(..., description="Calendar UID containing the events"),
    event_uids: List[str] = Field(..., description="List of event UIDs to delete"),
    mode: str = Field("continue", description="Operation mode: continue or fail_fast"),
    account: Optional[str] = Field(None, description="Account alias (uses default if not specified)")
) -> Dict[str, Any]:
    """
    Delete multiple events. Simple and straightforward.
    
    Modes:
    - continue: Process all deletions, report individual failures
    - fail_fast: Stop on first error
    """
    request_id = str(uuid.uuid4())
    
    try:
        # Validate mode
        if mode not in ["continue", "fail_fast"]:
            raise ValueError(f"Invalid mode '{mode}'. Must be one of: continue, fail_fast")
        
        
        results = {
            'total': len(event_uids),
            'succeeded': 0,
            'failed': 0,
            'details': []
        }
        
        for uid in event_uids:
            try:
                # Use event_manager directly (no await)
                event_manager.delete_event(
                    calendar_uid=calendar_uid,
                    event_uid=uid,
                    account_alias=account,
                    request_id=request_id
                )
                results['succeeded'] += 1
                results['details'].append({
                    'uid': uid,
                    'success': True
                })
                
            except Exception as e:
                results['failed'] += 1
                results['details'].append({
                    'uid': uid,
                    'success': False,
                    'error': str(e)
                })
                
                if mode == "fail_fast":
                    break
        
        results['success'] = results['failed'] == 0
        results['request_id'] = request_id
        return results
        
    except ValidationError as e:
        return {
            "success": False,
            "error": str(e),
            "error_code": "VALIDATION_ERROR",
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Bulk delete failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Bulk delete failed: {str(e)}",
            details={
                "tool": "bulk_delete_events",
                "calendar_uid": calendar_uid,
                "event_count": len(event_uids),
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in bulk_delete_events: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


@mcp.tool
async def bulk_create_tasks(
    calendar_uid: str = Field(..., description="Calendar UID to create tasks in"),
    tasks: List[Dict[str, Any]] = Field(..., description="List of task data dictionaries"),
    mode: str = Field("continue", description="Operation mode: continue, fail_fast, or atomic"),
    max_parallel: int = Field(5, description="Maximum parallel operations"),
    validate_before_execute: bool = Field(True, description="Validate all tasks before execution"),
    dry_run: bool = Field(False, description="Simulate the operation without making changes"),
    account: Optional[str] = Field(None, description="Account alias (uses default if not specified)")
) -> Dict[str, Any]:
    """
    Create multiple tasks with configurable error handling and validation.
    
    Modes:
    - continue: Process all tasks, report individual failures
    - fail_fast: Stop on first error
    - atomic: All succeed or all fail (with rollback)
    
    Each task dict should contain: summary, and optional fields like
    description, due, priority, status, percent_complete, related_to, etc.
    """
    request_id = str(uuid.uuid4())
    
    try:
        # Validate mode
        if mode not in ["continue", "fail_fast", "atomic"]:
            raise ValueError(f"Invalid mode '{mode}'. Must be one of: continue, fail_fast, atomic")
        
        # Create bulk options
        bulk_mode = {
            "continue": BulkOperationMode.CONTINUE_ON_ERROR,
            "fail_fast": BulkOperationMode.FAIL_FAST,
            "atomic": BulkOperationMode.ATOMIC
        }[mode]
        
        options = BulkOptions(
            mode=bulk_mode,
            max_parallel=max_parallel,
            validate_before_execute=validate_before_execute,
            dry_run=dry_run
        )
        
        # Execute bulk operation
        result = bulk_manager.bulk_create_tasks(calendar_uid, tasks, options, account)
        
        return {
            "success": result.failed == 0,
            "total": result.total,
            "successful": result.successful,
            "failed": result.failed,
            "success_rate": result.success_rate,
            "duration_ms": result.duration_ms,
            "results": [
                {
                    "index": r.index,
                    "success": r.success,
                    "uid": r.uid,
                    "error": r.error,
                    "duration_ms": r.duration_ms
                }
                for r in result.results
            ],
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Chronos error in bulk_create_tasks: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Bulk task creation failed: {str(e)}",
            details={
                "tool": "bulk_create_tasks",
                "calendar_uid": calendar_uid,
                "task_count": len(tasks),
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in bulk_create_tasks: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


@mcp.tool
async def bulk_delete_tasks(
    calendar_uid: str = Field(..., description="Calendar UID"),
    task_uids: List[str] = Field(..., description="List of task UIDs to delete"),
    mode: str = Field("continue", description="Operation mode: continue or fail_fast"),
    max_parallel: int = Field(5, description="Maximum parallel operations"),
    dry_run: bool = Field(False, description="Simulate the operation without making changes"),
    account: Optional[str] = Field(None, description="Account alias")
) -> Dict[str, Any]:
    """Delete multiple tasks efficiently."""
    request_id = str(uuid.uuid4())
    
    try:
        # Validate mode
        if mode not in ["continue", "fail_fast"]:
            raise ValueError(f"Invalid mode '{mode}'. Must be one of: continue, fail_fast")
        
        # Create bulk options
        bulk_mode = {
            "continue": BulkOperationMode.CONTINUE_ON_ERROR,
            "fail_fast": BulkOperationMode.FAIL_FAST
        }[mode]
        
        options = BulkOptions(
            mode=bulk_mode,
            max_parallel=max_parallel,
            dry_run=dry_run
        )
        
        # Execute bulk operation
        result = bulk_manager.bulk_delete_tasks(calendar_uid, task_uids, options)
        
        return {
            "success": result.failed == 0,
            "total": result.total,
            "successful": result.successful,
            "failed": result.failed,
            "success_rate": result.success_rate,
            "duration_ms": result.duration_ms,
            "results": [
                {
                    "index": r.index,
                    "success": r.success,
                    "uid": r.uid,
                    "error": r.error,
                    "duration_ms": r.duration_ms
                }
                for r in result.results
            ],
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Chronos error in bulk_delete_tasks: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Bulk task deletion failed: {str(e)}",
            details={
                "tool": "bulk_delete_tasks",
                "calendar_uid": calendar_uid,
                "task_count": len(task_uids),
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in bulk_delete_tasks: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


# ============= Task Management Tools =============

@mcp.tool
async def create_task(
    calendar_uid: str = Field(..., description="Calendar UID"),
    summary: str = Field(..., description="Task title/summary"),
    description: Optional[str] = Field(None, description="Task description"),
    due: Optional[str] = Field(None, description="Task due date (ISO format)"),
    priority: Optional[Union[int, str]] = Field(None, description="Task priority (1-9, 1 is highest)"),
    status: str = Field("NEEDS-ACTION", description="Task status (NEEDS-ACTION, IN-PROCESS, COMPLETED, CANCELLED)"),
    related_to: Optional[List[str]] = Field(None, description="List of related component UIDs"),
    account: Optional[str] = Field(None, description="Account alias")
) -> Dict[str, Any]:
    """Create a new task"""
    from .utils import parse_datetime
    from .validation import InputValidator, ValidationError
    from .models import TaskStatus
    
    request_id = str(uuid.uuid4())
    
    # Handle type conversion for parameters that might come as strings from MCP
    if priority is not None:
        try:
            priority = int(priority)
        except (ValueError, TypeError):
            return {
                "success": False,
                "error": f"Invalid priority value: {priority}. Must be an integer between 1 and 9",
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id
            }
    
    try:
        # Validate and sanitize text inputs
        try:
            summary = InputValidator.validate_text_field(summary, 'summary', required=True)
            if description:
                description = InputValidator.validate_text_field(description, 'description')
        except ValidationError as e:
            return {
                "success": False,
                "error": str(e),
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id
            }
        
        # Parse due date if provided
        due_dt = None
        if due:
            due_dt = parse_datetime(due)
        
        # Validate priority
        if priority is not None and not (1 <= priority <= 9):
            return {
                "success": False,
                "error": "Priority must be between 1 and 9",
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id
            }
        
        # Parse status
        try:
            task_status = TaskStatus(status)
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid status: {status}. Must be one of: NEEDS-ACTION, IN-PROCESS, COMPLETED, CANCELLED",
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id
            }
        
        task = task_manager.create_task(
            calendar_uid=calendar_uid,
            summary=summary,
            description=description,
            due=due_dt,
            priority=priority,
            status=task_status,
            related_to=related_to,
            account_alias=account,
            request_id=request_id
        )
        
        return {
            "success": True,
            "task": {
                "uid": task.uid,
                "summary": task.summary,
                "description": task.description,
                "due": task.due.isoformat() if task.due else None,
                "priority": task.priority,
                "status": task.status.value,
                "percent_complete": task.percent_complete,
                "related_to": task.related_to
            },
            "request_id": request_id
        }
        
    except (CalendarNotFoundError, EventCreationError) as e:
        e.request_id = request_id
        logger.error(f"Task creation error: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Create task failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Failed to create task: {str(e)}",
            details={
                "tool": "create_task",
                "summary": summary,
                "calendar_uid": calendar_uid,
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in create_task: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


@mcp.tool
async def list_tasks(
    calendar_uid: str = Field(..., description="Calendar UID"),
    account: Optional[str] = Field(None, description="Account alias")
) -> Dict[str, Any]:
    """List all tasks in a calendar"""
    request_id = str(uuid.uuid4())
    
    try:
        tasks = task_manager.list_tasks(
            calendar_uid=calendar_uid,
            account_alias=account,
            request_id=request_id
        )
        
        return {
            "tasks": [
                {
                    "uid": task.uid,
                    "summary": task.summary,
                    "description": task.description,
                    "due": task.due.isoformat() if task.due else None,
                    "priority": task.priority,
                    "status": task.status.value,
                    "percent_complete": task.percent_complete,
                    "categories": task.categories
                }
                for task in tasks
            ],
            "total": len(tasks),
            "request_id": request_id
        }
        
    except CalendarNotFoundError as e:
        e.request_id = request_id
        logger.error(f"Calendar not found for list_tasks: {e}")
        
        return {
            "tasks": [],
            "total": 0,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"List tasks failed: {e}")
        
        return {
            "tasks": [],
            "total": 0,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Failed to list tasks: {str(e)}",
            details={
                "tool": "list_tasks",
                "calendar_uid": calendar_uid,
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in list_tasks: {chronos_error}")
        
        return {
            "tasks": [],
            "total": 0,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


@mcp.tool
async def update_task(
    calendar_uid: str = Field(..., description="Calendar UID"),
    task_uid: str = Field(..., description="Task UID to update"),
    summary: Optional[str] = Field(None, description="Task title/summary"),
    description: Optional[str] = Field(None, description="Task description"),
    due: Optional[str] = Field(None, description="Task due date (ISO format)"),
    priority: Optional[Union[int, str]] = Field(None, description="Task priority (1-9, 1 is highest)"),
    status: Optional[str] = Field(None, description="Task status"),
    percent_complete: Optional[Union[int, str]] = Field(None, description="Completion percentage (0-100)"),
    account: Optional[str] = Field(None, description="Account alias")
) -> Dict[str, Any]:
    """Update an existing task. Only provided fields will be updated."""
    from .utils import parse_datetime
    from .validation import InputValidator, ValidationError
    from .models import TaskStatus
    
    request_id = str(uuid.uuid4())
    
    # Handle type conversion for parameters that might come as strings from MCP
    if priority is not None:
        try:
            priority = int(priority)
        except (ValueError, TypeError):
            return {
                "success": False,
                "error": f"Invalid priority value: {priority}. Must be an integer between 1 and 9",
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id
            }
    
    if percent_complete is not None:
        try:
            percent_complete = int(percent_complete)
        except (ValueError, TypeError):
            return {
                "success": False,
                "error": f"Invalid percent_complete value: {percent_complete}. Must be an integer between 0 and 100",
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id
            }
    
    try:
        # Validate text inputs if provided
        try:
            if summary is not None:
                summary = InputValidator.validate_text_field(summary, 'summary', required=True)
            if description is not None:
                description = InputValidator.validate_text_field(description, 'description')
        except ValidationError as e:
            return {
                "success": False,
                "error": str(e),
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id
            }
        
        # Parse due date if provided
        due_dt = None
        if due is not None:
            due_dt = parse_datetime(due) if due else None
        
        # Validate priority if provided
        if priority is not None and not (1 <= priority <= 9):
            return {
                "success": False,
                "error": "Priority must be between 1 and 9",
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id
            }
        
        # Parse status if provided
        task_status = None
        if status is not None:
            try:
                task_status = TaskStatus(status)
            except ValueError:
                return {
                    "success": False,
                    "error": f"Invalid status: {status}",
                    "error_code": "VALIDATION_ERROR",
                    "request_id": request_id
                }
        
        # Validate percent_complete if provided
        if percent_complete is not None and not (0 <= percent_complete <= 100):
            return {
                "success": False,
                "error": "Percent complete must be between 0 and 100",
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id
            }
        
        updated_task = task_manager.update_task(
            task_uid=task_uid,
            calendar_uid=calendar_uid,
            summary=summary,
            description=description,
            due=due_dt,
            priority=priority,
            status=task_status,
            percent_complete=percent_complete,
            account_alias=account,
            request_id=request_id
        )
        
        return {
            "success": True,
            "task": {
                "uid": updated_task.uid,
                "summary": updated_task.summary,
                "description": updated_task.description,
                "due": updated_task.due.isoformat() if updated_task.due else None,
                "priority": updated_task.priority,
                "status": updated_task.status.value,
                "percent_complete": updated_task.percent_complete,
                "categories": updated_task.categories
            },
            "message": f"Task '{task_uid}' updated successfully",
            "request_id": request_id
        }
        
    except EventNotFoundError as e:
        e.request_id = request_id
        logger.error(f"Task not found for update: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except (CalendarNotFoundError, EventCreationError) as e:
        e.request_id = request_id
        logger.error(f"Update task failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Update task failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Failed to update task: {str(e)}",
            details={
                "tool": "update_task",
                "task_uid": task_uid,
                "calendar_uid": calendar_uid,
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in update_task: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


@mcp.tool
async def delete_task(
    calendar_uid: str = Field(..., description="Calendar UID"),
    task_uid: str = Field(..., description="Task UID to delete"),
    account: Optional[str] = Field(None, description="Account alias")
) -> Dict[str, Any]:
    """Delete a task"""
    request_id = str(uuid.uuid4())
    
    try:
        task_manager.delete_task(
            calendar_uid=calendar_uid,
            task_uid=task_uid,
            account_alias=account,
            request_id=request_id
        )
        
        return {
            "success": True,
            "message": f"Task '{task_uid}' deleted successfully",
            "request_id": request_id
        }
        
    except EventNotFoundError as e:
        e.request_id = request_id
        logger.error(f"Task not found for deletion: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except CalendarNotFoundError as e:
        e.request_id = request_id
        logger.error(f"Calendar not found for task deletion: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Delete task failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Failed to delete task: {str(e)}",
            details={
                "tool": "delete_task",
                "task_uid": task_uid,
                "calendar_uid": calendar_uid,
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in delete_task: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


@mcp.tool
async def bulk_create_journals(
    calendar_uid: str = Field(..., description="Calendar UID to create journals in"),
    journals: List[Dict[str, Any]] = Field(..., description="List of journal data dictionaries"),
    mode: str = Field("continue", description="Operation mode: continue, fail_fast, or atomic"),
    max_parallel: int = Field(5, description="Maximum parallel operations"),
    validate_before_execute: bool = Field(True, description="Validate all journals before execution"),
    dry_run: bool = Field(False, description="Simulate the operation without making changes"),
    account: Optional[str] = Field(None, description="Account alias (uses default if not specified)")
) -> Dict[str, Any]:
    """
    Create multiple journal entries with configurable error handling and validation.
    
    Modes:
    - continue: Process all journals, report individual failures
    - fail_fast: Stop on first error
    - atomic: All succeed or all fail (with rollback)
    
    Each journal dict should contain: summary, and optional fields like
    description, dtstart, categories, related_to, etc.
    """
    request_id = str(uuid.uuid4())
    
    try:
        # Validate mode
        if mode not in ["continue", "fail_fast", "atomic"]:
            raise ValueError(f"Invalid mode '{mode}'. Must be one of: continue, fail_fast, atomic")
        
        # Create bulk options
        bulk_mode = {
            "continue": BulkOperationMode.CONTINUE_ON_ERROR,
            "fail_fast": BulkOperationMode.FAIL_FAST,
            "atomic": BulkOperationMode.ATOMIC
        }[mode]
        
        options = BulkOptions(
            mode=bulk_mode,
            max_parallel=max_parallel,
            validate_before_execute=validate_before_execute,
            dry_run=dry_run
        )
        
        # Execute bulk operation
        result = bulk_manager.bulk_create_journals(calendar_uid, journals, options, account)
        
        return {
            "success": result.failed == 0,
            "total": result.total,
            "successful": result.successful,
            "failed": result.failed,
            "success_rate": result.success_rate,
            "duration_ms": result.duration_ms,
            "results": [
                {
                    "index": r.index,
                    "success": r.success,
                    "uid": r.uid,
                    "error": r.error,
                    "duration_ms": r.duration_ms
                }
                for r in result.results
            ],
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Chronos error in bulk_create_journals: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Bulk journal creation failed: {str(e)}",
            details={
                "tool": "bulk_create_journals",
                "calendar_uid": calendar_uid,
                "journal_count": len(journals),
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in bulk_create_journals: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


@mcp.tool
async def bulk_delete_journals(
    calendar_uid: str = Field(..., description="Calendar UID"),
    journal_uids: List[str] = Field(..., description="List of journal UIDs to delete"),
    mode: str = Field("continue", description="Operation mode: continue or fail_fast"),
    max_parallel: int = Field(5, description="Maximum parallel operations"),
    dry_run: bool = Field(False, description="Simulate the operation without making changes"),
    account: Optional[str] = Field(None, description="Account alias")
) -> Dict[str, Any]:
    """Delete multiple journal entries efficiently."""
    request_id = str(uuid.uuid4())
    
    try:
        # Validate mode
        if mode not in ["continue", "fail_fast"]:
            raise ValueError(f"Invalid mode '{mode}'. Must be one of: continue, fail_fast")
        
        # Create bulk options
        bulk_mode = {
            "continue": BulkOperationMode.CONTINUE_ON_ERROR,
            "fail_fast": BulkOperationMode.FAIL_FAST
        }[mode]
        
        options = BulkOptions(
            mode=bulk_mode,
            max_parallel=max_parallel,
            dry_run=dry_run
        )
        
        # Execute bulk operation
        result = bulk_manager.bulk_delete_journals(calendar_uid, journal_uids, options)
        
        return {
            "success": result.failed == 0,
            "total": result.total,
            "successful": result.successful,
            "failed": result.failed,
            "success_rate": result.success_rate,
            "duration_ms": result.duration_ms,
            "results": [
                {
                    "index": r.index,
                    "success": r.success,
                    "uid": r.uid,
                    "error": r.error,
                    "duration_ms": r.duration_ms
                }
                for r in result.results
            ],
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Chronos error in bulk_delete_journals: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Bulk journal deletion failed: {str(e)}",
            details={
                "tool": "bulk_delete_journals",
                "calendar_uid": calendar_uid,
                "journal_count": len(journal_uids),
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in bulk_delete_journals: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


# ============= Journal Management Tools =============

@mcp.tool
async def create_journal(
    calendar_uid: str = Field(..., description="Calendar UID"),
    summary: str = Field(..., description="Journal title/summary"),
    description: Optional[str] = Field(None, description="Journal content"),
    dtstart: Optional[str] = Field(None, description="Journal entry date/time (ISO format)"),
    related_to: Optional[List[str]] = Field(None, description="List of related component UIDs"),
    account: Optional[str] = Field(None, description="Account alias")
) -> Dict[str, Any]:
    """Create a new journal entry"""
    from .utils import parse_datetime
    from .validation import InputValidator, ValidationError
    
    request_id = str(uuid.uuid4())
    
    try:
        # Validate and sanitize text inputs
        try:
            summary = InputValidator.validate_text_field(summary, 'summary', required=True)
            if description:
                description = InputValidator.validate_text_field(description, 'description')
        except ValidationError as e:
            return {
                "success": False,
                "error": str(e),
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id
            }
        
        # Parse dtstart if provided
        dtstart_dt = None
        if dtstart:
            dtstart_dt = parse_datetime(dtstart)
        
        journal = journal_manager.create_journal(
            calendar_uid=calendar_uid,
            summary=summary,
            description=description,
            dtstart=dtstart_dt,
            related_to=related_to,
            account_alias=account,
            request_id=request_id
        )
        
        return {
            "success": True,
            "journal": {
                "uid": journal.uid,
                "summary": journal.summary,
                "description": journal.description,
                "dtstart": journal.dtstart.isoformat(),
                "categories": journal.categories,
                "related_to": journal.related_to
            },
            "request_id": request_id
        }
        
    except (CalendarNotFoundError, EventCreationError) as e:
        e.request_id = request_id
        logger.error(f"Journal creation error: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Create journal failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Failed to create journal: {str(e)}",
            details={
                "tool": "create_journal",
                "summary": summary,
                "calendar_uid": calendar_uid,
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in create_journal: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


@mcp.tool
async def list_journals(
    calendar_uid: str = Field(..., description="Calendar UID"),
    account: Optional[str] = Field(None, description="Account alias")
) -> Dict[str, Any]:
    """List all journals in a calendar"""
    request_id = str(uuid.uuid4())
    
    try:
        journals = journal_manager.list_journals(
            calendar_uid=calendar_uid,
            account_alias=account,
            request_id=request_id
        )
        
        return {
            "journals": [
                {
                    "uid": journal.uid,
                    "summary": journal.summary,
                    "description": journal.description,
                    "dtstart": journal.dtstart.isoformat(),
                    "categories": journal.categories
                }
                for journal in journals
            ],
            "total": len(journals),
            "request_id": request_id
        }
        
    except CalendarNotFoundError as e:
        e.request_id = request_id
        logger.error(f"Calendar not found for list_journals: {e}")
        
        return {
            "journals": [],
            "total": 0,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"List journals failed: {e}")
        
        return {
            "journals": [],
            "total": 0,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Failed to list journals: {str(e)}",
            details={
                "tool": "list_journals",
                "calendar_uid": calendar_uid,
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in list_journals: {chronos_error}")
        
        return {
            "journals": [],
            "total": 0,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


@mcp.tool
async def update_journal(
    calendar_uid: str = Field(..., description="Calendar UID"),
    journal_uid: str = Field(..., description="Journal UID to update"),
    summary: Optional[str] = Field(None, description="Journal title/summary"),
    description: Optional[str] = Field(None, description="Journal content"),
    dtstart: Optional[str] = Field(None, description="Journal entry date/time (ISO format)"),
    account: Optional[str] = Field(None, description="Account alias")
) -> Dict[str, Any]:
    """Update an existing journal. Only provided fields will be updated."""
    from .utils import parse_datetime
    from .validation import InputValidator, ValidationError
    
    request_id = str(uuid.uuid4())
    
    try:
        # Validate text inputs if provided
        try:
            if summary is not None:
                summary = InputValidator.validate_text_field(summary, 'summary', required=True)
            if description is not None:
                description = InputValidator.validate_text_field(description, 'description')
        except ValidationError as e:
            return {
                "success": False,
                "error": str(e),
                "error_code": "VALIDATION_ERROR",
                "request_id": request_id
            }
        
        # Parse dtstart if provided
        dtstart_dt = None
        if dtstart is not None:
            dtstart_dt = parse_datetime(dtstart) if dtstart else None
        
        updated_journal = journal_manager.update_journal(
            journal_uid=journal_uid,
            calendar_uid=calendar_uid,
            summary=summary,
            description=description,
            dtstart=dtstart_dt,
            account_alias=account,
            request_id=request_id
        )
        
        return {
            "success": True,
            "journal": {
                "uid": updated_journal.uid,
                "summary": updated_journal.summary,
                "description": updated_journal.description,
                "dtstart": updated_journal.dtstart.isoformat(),
                "categories": updated_journal.categories
            },
            "message": f"Journal '{journal_uid}' updated successfully",
            "request_id": request_id
        }
        
    except EventNotFoundError as e:
        e.request_id = request_id
        logger.error(f"Journal not found for update: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except (CalendarNotFoundError, EventCreationError) as e:
        e.request_id = request_id
        logger.error(f"Update journal failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Update journal failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Failed to update journal: {str(e)}",
            details={
                "tool": "update_journal",
                "journal_uid": journal_uid,
                "calendar_uid": calendar_uid,
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in update_journal: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


@mcp.tool
async def delete_journal(
    calendar_uid: str = Field(..., description="Calendar UID"),
    journal_uid: str = Field(..., description="Journal UID to delete"),
    account: Optional[str] = Field(None, description="Account alias")
) -> Dict[str, Any]:
    """Delete a journal"""
    request_id = str(uuid.uuid4())
    
    try:
        journal_manager.delete_journal(
            calendar_uid=calendar_uid,
            journal_uid=journal_uid,
            account_alias=account,
            request_id=request_id
        )
        
        return {
            "success": True,
            "message": f"Journal '{journal_uid}' deleted successfully",
            "request_id": request_id
        }
        
    except EventNotFoundError as e:
        e.request_id = request_id
        logger.error(f"Journal not found for deletion: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except CalendarNotFoundError as e:
        e.request_id = request_id
        logger.error(f"Calendar not found for journal deletion: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except ChronosError as e:
        e.request_id = request_id
        logger.error(f"Delete journal failed: {e}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(e),
            "error_code": e.error_code,
            "request_id": request_id
        }
        
    except Exception as e:
        chronos_error = ChronosError(
            message=f"Failed to delete journal: {str(e)}",
            details={
                "tool": "delete_journal",
                "journal_uid": journal_uid,
                "calendar_uid": calendar_uid,
                "original_error": str(e),
                "original_type": type(e).__name__
            },
            request_id=request_id
        )
        logger.error(f"Unexpected error in delete_journal: {chronos_error}")
        
        return {
            "success": False,
            "error": ErrorSanitizer.get_user_friendly_message(chronos_error),
            "error_code": chronos_error.error_code,
            "request_id": request_id
        }


# ============= Main Entry Point =============

if __name__ == "__main__":
    # Run the server
    mcp.run()
