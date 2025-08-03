"""
Unit tests for bulk event creation functionality
"""

import json
from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from chronos_mcp.exceptions import ChronosError
# Import the actual function directly
from chronos_mcp.server import bulk_create_events


class TestBulkCreateEvents:
    """Test the bulk_create_events function"""

    @pytest.fixture
    def mock_managers(self):
        """Setup mock managers"""
        with (
            patch("chronos_mcp.server.event_manager") as mock_event,
            patch("chronos_mcp.server.logger") as mock_logger,
        ):
            yield {"event": mock_event, "logger": mock_logger}

    @pytest.fixture
    def valid_events(self):
        """Valid event data for testing"""
        return [
            {
                "summary": "Event 1",
                "dtstart": "2025-01-20T10:00:00",
                "dtend": "2025-01-20T11:00:00",
                "description": "Test event 1",
            },
            {
                "summary": "Event 2",
                "dtstart": "2025-01-21T14:00:00",
                "dtend": "2025-01-21T15:00:00",
                "location": "Room B",
            },
            {
                "summary": "Event 3",
                "dtstart": "2025-01-22T09:00:00",
                "dtend": "2025-01-22T10:00:00",
                "all_day": False,
                "alarm_minutes": "15",
            },
        ]

    @pytest.mark.asyncio
    async def test_bulk_create_success(self, mock_managers, valid_events):
        """Test successful bulk creation"""
        # Mock successful event creation
        created_events = []
        for i, event_data in enumerate(valid_events):
            created_event = Mock()
            created_event.uid = f"created-{i}"
            created_events.append(created_event)

        mock_managers["event"].create_event.side_effect = created_events

        result = await bulk_create_events.fn(
            calendar_uid="test-cal",
            events=valid_events,
            mode="continue",
            validate_before_execute=True,
            account=None,
        )

        assert result["success"] is True
        assert result["total"] == 3
        assert result["succeeded"] == 3
        assert result["failed"] == 0
        assert len(result["details"]) == 3

        # Check each detail
        for i, detail in enumerate(result["details"]):
            assert detail["success"] is True
            assert detail["uid"] == f"created-{i}"
            assert detail["summary"] == valid_events[i]["summary"]

    @pytest.mark.asyncio
    async def test_bulk_create_validation_error(self, mock_managers):
        """Test validation errors"""
        invalid_events = [
            {
                "summary": "Valid Event",
                "dtstart": "2025-01-20T10:00:00",
                "dtend": "2025-01-20T11:00:00",
            },
            {
                # Missing summary
                "dtstart": "2025-01-21T14:00:00",
                "dtend": "2025-01-21T15:00:00",
            },
        ]

        # Direct function call
        result = await bulk_create_events.fn(
            calendar_uid="test-cal",
            events=invalid_events,
            mode="continue",
            validate_before_execute=True,
            account=None,
        )

        assert result["success"] is False
        assert "missing required 'summary'" in result["error"]

    @pytest.mark.asyncio
    async def test_bulk_create_continue_mode(self, mock_managers, valid_events):
        """Test continue mode with partial failures"""

        # Mock mixed success/failure
        def create_side_effect(*args, **kwargs):
            summary = kwargs.get("summary")
            if summary == "Event 2":
                raise ChronosError("Creation failed")
            event = Mock()
            event.uid = f"uid-{summary}"
            return event

        mock_managers["event"].create_event.side_effect = create_side_effect

        # Direct function call
        result = await bulk_create_events.fn(
            calendar_uid="test-cal",
            events=valid_events,
            mode="continue",
            validate_before_execute=True,
            account=None,
        )

        assert result["success"] is False
        assert result["total"] == 3
        assert result["succeeded"] == 2
        assert result["failed"] == 1

        # Check failed event
        failed = [d for d in result["details"] if not d["success"]][0]
        assert failed["index"] == 1
        assert "Creation failed" in failed["error"]

    @pytest.mark.asyncio
    async def test_bulk_create_fail_fast_mode(self, mock_managers, valid_events):
        """Test fail_fast mode stops on first error"""

        # Mock failure on second event
        def create_side_effect(*args, **kwargs):
            summary = kwargs.get("summary")
            if summary == "Event 2":
                raise ChronosError("Creation failed")
            event = Mock()
            event.uid = f"uid-{summary}"
            return event

        mock_managers["event"].create_event.side_effect = create_side_effect

        # Direct function call
        result = await bulk_create_events.fn(
            calendar_uid="test-cal",
            events=valid_events,
            mode="fail_fast",
            validate_before_execute=True,
            account=None,
        )

        assert result["success"] is False
        assert result["total"] == 3
        assert result["succeeded"] == 1
        assert result["failed"] == 1
        assert len(result["details"]) == 2  # Stopped after failure

    @pytest.mark.asyncio
    async def test_bulk_create_invalid_mode(self, mock_managers, valid_events):
        """Test invalid mode validation"""
        # Direct function call
        result = await bulk_create_events.fn(
            calendar_uid="test-cal",
            events=valid_events,
            mode="atomic",  # Invalid mode
            validate_before_execute=True,
            account=None,
        )

        assert result["success"] is False
        assert "Invalid mode" in result["error"]

    @pytest.mark.asyncio
    async def test_bulk_create_datetime_parsing(self, mock_managers):
        """Test datetime parsing"""
        events = [
            {
                "summary": "Test Event",
                "dtstart": "2025-01-20T10:00:00Z",
                "dtend": "2025-01-20T11:00:00Z",
            }
        ]

        created_event = Mock()
        created_event.uid = "test-uid"
        mock_managers["event"].create_event.return_value = created_event

        # Direct function call
        result = await bulk_create_events.fn(
            calendar_uid="test-cal",
            events=events,
            mode="continue",
            validate_before_execute=True,
            account=None,
        )

        # Check that datetime objects were passed
        call_args = mock_managers["event"].create_event.call_args[1]
        assert isinstance(call_args["start"], datetime)
        assert isinstance(call_args["end"], datetime)

    @pytest.mark.asyncio
    async def test_bulk_create_attendees_parsing(self, mock_managers):
        """Test attendees JSON parsing"""
        attendees = [{"email": "test@example.com", "name": "Test User"}]
        events = [
            {
                "summary": "Meeting",
                "dtstart": "2025-01-20T10:00:00",
                "dtend": "2025-01-20T11:00:00",
                "attendees_json": json.dumps(attendees),
            }
        ]

        created_event = Mock()
        created_event.uid = "test-uid"
        mock_managers["event"].create_event.return_value = created_event

        # Direct function call
        result = await bulk_create_events.fn(
            calendar_uid="test-cal",
            events=events,
            mode="continue",
            validate_before_execute=True,
            account=None,
        )

        # Check attendees were parsed
        call_args = mock_managers["event"].create_event.call_args[1]
        assert call_args["attendees"] == attendees

    @pytest.mark.asyncio
    async def test_bulk_create_invalid_attendees_json(self, mock_managers):
        """Test invalid attendees JSON handling"""
        events = [
            {
                "summary": "Meeting",
                "dtstart": "2025-01-20T10:00:00",
                "dtend": "2025-01-20T11:00:00",
                "attendees_json": "not-valid-json",
            }
        ]

        created_event = Mock()
        created_event.uid = "test-uid"
        mock_managers["event"].create_event.return_value = created_event

        # Direct function call
        result = await bulk_create_events.fn(
            calendar_uid="test-cal",
            events=events,
            mode="continue",
            validate_before_execute=True,
            account=None,
        )

        # Should log warning but continue
        mock_managers["logger"].warning.assert_called()
        call_args = mock_managers["event"].create_event.call_args[1]
        assert call_args["attendees"] == []

    @pytest.mark.asyncio
    async def test_bulk_create_alarm_parsing(self, mock_managers):
        """Test alarm minutes parsing"""
        events = [
            {
                "summary": "Meeting",
                "dtstart": "2025-01-20T10:00:00",
                "dtend": "2025-01-20T11:00:00",
                "alarm_minutes": "30",
            }
        ]

        created_event = Mock()
        created_event.uid = "test-uid"
        mock_managers["event"].create_event.return_value = created_event

        # Direct function call
        result = await bulk_create_events.fn(
            calendar_uid="test-cal",
            events=events,
            mode="continue",
            validate_before_execute=True,
            account=None,
        )

        # Check alarm was parsed to int
        call_args = mock_managers["event"].create_event.call_args[1]
        assert call_args["alarm_minutes"] == 30

    @pytest.mark.asyncio
    async def test_bulk_create_empty_list(self, mock_managers):
        """Test empty event list"""
        # Direct function call
        result = await bulk_create_events.fn(
            calendar_uid="test-cal",
            events=[],
            mode="continue",
            validate_before_execute=True,
            account=None,
        )

        assert result["success"] is True
        assert result["total"] == 0
        assert result["succeeded"] == 0
        assert result["failed"] == 0
