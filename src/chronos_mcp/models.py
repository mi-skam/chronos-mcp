"""
Data models for Chronos MCP
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, field_validator


class AccountStatus(str, Enum):
    """Account connection status"""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    UNKNOWN = "unknown"


class EventStatus(str, Enum):
    """Event status values"""

    TENTATIVE = "TENTATIVE"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class TaskStatus(str, Enum):
    """Task status values"""

    NEEDS_ACTION = "NEEDS-ACTION"
    IN_PROCESS = "IN-PROCESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class AttendeeRole(str, Enum):
    """Attendee roles"""

    CHAIR = "CHAIR"
    REQ_PARTICIPANT = "REQ-PARTICIPANT"
    OPT_PARTICIPANT = "OPT-PARTICIPANT"
    NON_PARTICIPANT = "NON-PARTICIPANT"


class AttendeeStatus(str, Enum):
    """Attendee participation status"""

    NEEDS_ACTION = "NEEDS-ACTION"
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    TENTATIVE = "TENTATIVE"
    DELEGATED = "DELEGATED"


class Account(BaseModel):
    """CalDAV account configuration"""

    alias: str = Field(..., description="Account alias/identifier")
    url: HttpUrl = Field(..., description="CalDAV server URL")
    username: str = Field(..., description="Username for authentication")
    password: str | None = Field(
        None, description="Password (optional if using keyring)"
    )
    display_name: str | None = Field(None, description="Display name for the account")
    status: AccountStatus = Field(
        AccountStatus.UNKNOWN, description="Connection status"
    )
    last_sync: datetime | None = Field(None, description="Last successful sync time")

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, v: str | None) -> str | None:
        """Validate password for security (defense-in-depth)"""
        if v is not None and v != "":
            from .exceptions import ValidationError as ChronosValidationError
            from .validation import InputValidator

            try:
                # Validate to prevent injection attacks at model layer
                return InputValidator.validate_text_field(v, "password", required=False)
            except ChronosValidationError as e:
                # Re-raise as Pydantic ValidationError for proper handling
                from pydantic_core import PydanticCustomError

                raise PydanticCustomError(
                    "password_validation",
                    "Password validation failed: {error}",
                    {"error": str(e)},
                )
        return v


class Calendar(BaseModel):
    """Calendar information"""

    uid: str = Field(..., description="Calendar unique identifier")
    name: str = Field(..., description="Calendar display name")
    description: str | None = Field(None, description="Calendar description")
    color: str | None = Field(None, description="Calendar color (hex)")
    account_alias: str = Field(..., description="Associated account alias")
    url: str | None = Field(None, description="Calendar URL")
    read_only: bool = Field(False, description="Whether calendar is read-only")


class Attendee(BaseModel):
    """Event attendee"""

    email: str = Field(..., description="Attendee email address")
    name: str | None = Field(None, description="Attendee display name")
    role: AttendeeRole = Field(
        AttendeeRole.REQ_PARTICIPANT, description="Attendee role"
    )
    status: AttendeeStatus = Field(
        AttendeeStatus.NEEDS_ACTION, description="Participation status"
    )
    rsvp: bool = Field(True, description="Whether RSVP is requested")


class Alarm(BaseModel):
    """Event reminder/alarm"""

    trigger: str = Field(
        ..., description="Trigger time (e.g., '-PT15M' for 15 minutes before)"
    )
    action: str = Field("DISPLAY", description="Alarm action type")
    description: str | None = Field(None, description="Alarm description")


class Event(BaseModel):
    """Calendar event"""

    uid: str = Field(..., description="Event unique identifier")
    summary: str = Field(..., description="Event title/summary")
    description: str | None = Field(None, description="Event description")
    start: datetime = Field(..., description="Event start time")
    end: datetime = Field(..., description="Event end time")
    all_day: bool = Field(False, description="Whether this is an all-day event")
    location: str | None = Field(None, description="Event location")
    status: EventStatus = Field(EventStatus.CONFIRMED, description="Event status")
    attendees: list[Attendee] = Field(
        default_factory=list, description="Event attendees"
    )
    alarms: list[Alarm] = Field(
        default_factory=list, description="Event alarms/reminders"
    )
    recurrence_rule: str | None = Field(None, description="RRULE for recurring events")
    recurrence_id: datetime | None = Field(
        None, description="Recurrence instance identifier"
    )
    calendar_uid: str = Field(..., description="Parent calendar UID")
    account_alias: str = Field(..., description="Associated account alias")
    categories: list[str] = Field(
        default_factory=list, description="Event categories/tags"
    )
    url: str | None = Field(None, description="Associated URL")
    related_to: list[str] = Field(
        default_factory=list, description="Related component UIDs"
    )


class Task(BaseModel):
    """Calendar task (VTODO)"""

    uid: str = Field(..., description="Task unique identifier")
    summary: str = Field(..., description="Task summary")
    description: str | None = Field(None, description="Task description")
    due: datetime | None = Field(None, description="Task due date")
    completed: datetime | None = Field(None, description="Task completion date")
    priority: int | None = Field(None, description="Task priority (1-9, 1 is highest)")
    status: TaskStatus = Field(TaskStatus.NEEDS_ACTION, description="Task status")
    percent_complete: int = Field(0, description="Completion percentage (0-100)")
    categories: list[str] = Field(
        default_factory=list, description="Task categories/tags"
    )
    related_to: list[str] = Field(
        default_factory=list, description="Related component UIDs"
    )
    calendar_uid: str = Field(..., description="Parent calendar UID")
    account_alias: str = Field(..., description="Associated account alias")


class Journal(BaseModel):
    """Calendar journal entry (VJOURNAL)"""

    uid: str = Field(..., description="Journal unique identifier")
    summary: str = Field(..., description="Journal title/summary")
    description: str | None = Field(None, description="Journal content")
    dtstart: datetime = Field(..., description="Journal entry date/time")
    categories: list[str] = Field(
        default_factory=list, description="Journal categories/tags"
    )
    related_to: list[str] = Field(
        default_factory=list, description="Related component UIDs"
    )
    calendar_uid: str = Field(..., description="Parent calendar UID")
    account_alias: str = Field(..., description="Associated account alias")
