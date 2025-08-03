"""
Unit tests for bulk operations
"""

from unittest.mock import MagicMock, Mock, patch

from chronos_mcp.bulk import (BulkOperationManager, BulkOperationMode,
                              BulkOptions, BulkResult, OperationResult)


class TestBulkOptions:
    def test_bulk_options_defaults(self):
        """Test BulkOptions default values"""
        opts = BulkOptions()

        assert opts.mode == BulkOperationMode.CONTINUE_ON_ERROR
        assert opts.max_parallel == 5
        assert opts.timeout_per_operation == 30
        assert opts.validate_before_execute is True
        assert opts.dry_run is False

    def test_bulk_operation_modes(self):
        """Test different bulk operation modes"""
        assert BulkOperationMode.ATOMIC.value == "atomic"
        assert BulkOperationMode.CONTINUE_ON_ERROR.value == "continue"
        assert BulkOperationMode.FAIL_FAST.value == "fail_fast"


class TestBulkResult:
    def test_bulk_result_properties(self):
        """Test BulkResult calculated properties"""
        result = BulkResult(total=10, successful=7, failed=3, duration_ms=1500.5)

        assert result.success_rate == 70.0

        # Add some results
        result.results = [
            OperationResult(index=0, success=True, uid="uid1"),
            OperationResult(index=1, success=False, error="Failed"),
            OperationResult(index=2, success=True, uid="uid2"),
        ]

        failures = result.get_failures()
        assert len(failures) == 1
        assert failures[0].index == 1

        successes = result.get_successes()
        assert len(successes) == 2
        assert successes[0].uid == "uid1"


class TestBulkOperationManager:
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_event_manager = Mock()
        self.bulk_manager = BulkOperationManager(self.mock_event_manager)

        # Sample events for testing
        self.test_events = [
            {
                "summary": "Event 1",
                "dtstart": "2025-07-10T10:00:00",
                "dtend": "2025-07-10T11:00:00",
            },
            {
                "summary": "Event 2",
                "dtstart": "2025-07-10T14:00:00",
                "dtend": "2025-07-10T15:00:00",
            },
        ]

    def test_validate_events_success(self):
        """Test event validation with valid events"""
        errors = self.bulk_manager._validate_events(self.test_events)
        assert len(errors) == 0

    def test_validate_events_missing_fields(self):
        """Test event validation with missing required fields"""
        invalid_events = [
            {"summary": "No dates"},  # Missing dtstart and dtend
            {
                "dtstart": "2025-07-10T10:00:00",
                "dtend": "2025-07-10T11:00:00",
            },  # Missing summary
            {
                "summary": "Invalid dates",
                "dtstart": "2025-07-10T11:00:00",
                "dtend": "2025-07-10T10:00:00",  # End before start
            },
        ]

        errors = self.bulk_manager._validate_events(invalid_events)
        assert (
            len(errors) == 5
        )  # 3 errors for first (missing dtstart, dtend, invalid date), 1 for second, 1 for third

        # Check specific errors
        error_messages = [err[1] for err in errors]
        assert any("Missing required field: dtstart" in msg for msg in error_messages)
        assert any("Missing required field: summary" in msg for msg in error_messages)
        assert any("End time before start time" in msg for msg in error_messages)

    def test_bulk_create_dry_run(self):
        """Test bulk create in dry run mode"""
        options = BulkOptions(dry_run=True)

        result = self.bulk_manager.bulk_create_events(
            calendar_uid="cal123", events=self.test_events, options=options
        )

        assert result.total == 2
        assert result.successful == 2
        assert result.failed == 0
        assert len(result.results) == 2

        # Event manager should not be called in dry run
        self.mock_event_manager.create_event.assert_not_called()

    def test_bulk_create_continue_on_error(self):
        """Test bulk create with continue on error mode"""
        # Mock event manager to fail on second event
        mock_event1 = Mock()
        mock_event1.uid = "created-1"
        self.mock_event_manager.create_event.side_effect = [
            mock_event1,  # Success
            Exception("Network error"),  # Failure
        ]

        options = BulkOptions(mode=BulkOperationMode.CONTINUE_ON_ERROR)

        result = self.bulk_manager.bulk_create_events(
            calendar_uid="cal123", events=self.test_events, options=options
        )

        assert result.total == 2
        assert result.successful == 1
        assert result.failed == 1
        assert self.mock_event_manager.create_event.call_count == 2

    def test_bulk_create_fail_fast(self):
        """Test bulk create with fail fast mode"""
        # Use smaller batch to test fail fast properly
        test_events = [
            {
                "summary": f"Event {i}",
                "dtstart": "2025-07-10T16:00:00",
                "dtend": "2025-07-10T17:00:00",
            }
            for i in range(1, 4)
        ]

        # Mock to fail on second event
        mock_event1 = Mock()
        mock_event1.uid = "created-1"
        mock_event3 = Mock()
        mock_event3.uid = "created-3"
        self.mock_event_manager.create_event.side_effect = [
            mock_event1,
            Exception("API limit reached"),
            mock_event3,
        ]

        options = BulkOptions(mode=BulkOperationMode.FAIL_FAST, max_parallel=2)

        result = self.bulk_manager.bulk_create_events(
            calendar_uid="cal123", events=test_events, options=options
        )

        # In fail_fast mode with batch processing
        assert result.failed >= 1  # At least one failure
        assert result.total == 3
        # Due to parallel batch processing, it may process 1-2 before stopping
        assert result.successful <= 2

    def test_bulk_create_parallel_execution(self):
        """Test that bulk operations execute in batches"""
        # Mock successful event creation
        mock_event1 = Mock()
        mock_event1.uid = "uid1"
        mock_event2 = Mock()
        mock_event2.uid = "uid2"

        self.mock_event_manager.create_event.side_effect = [mock_event1, mock_event2]

        options = BulkOptions(max_parallel=2)

        # Call the batch execution method directly
        results = self.bulk_manager._execute_batch_create(
            calendar_uid="cal123",
            batch=self.test_events,
            start_idx=0,
            options=options,
            account_alias=None,
        )

        # Should have created 2 events
        assert self.mock_event_manager.create_event.call_count == 2
        assert len(results) == 2
        assert all(r.success for r in results)
        assert results[0].uid == "uid1"
        assert results[1].uid == "uid2"


class TestBulkDelete:
    def setup_method(self):
        """Set up test fixtures"""
        self.mock_event_manager = Mock()
        self.bulk_manager = BulkOperationManager(self.mock_event_manager)
        self.test_uids = ["uid1", "uid2", "uid3"]

    def test_bulk_delete_success(self):
        """Test successful bulk delete"""
        # Mock successful deletions
        self.mock_event_manager.delete_event.return_value = True

        options = BulkOptions()
        result = self.bulk_manager.bulk_delete_events(
            calendar_uid="cal123", event_uids=self.test_uids, options=options
        )

        assert result.total == 3
        assert result.successful == 3
        assert result.failed == 0
        assert self.mock_event_manager.delete_event.call_count == 3

    def test_bulk_delete_with_failures(self):
        """Test bulk delete with some failures"""
        # Mock mixed results
        self.mock_event_manager.delete_event.side_effect = [
            True,  # Success
            Exception("Event not found"),  # Failure
            True,  # Success
        ]

        options = BulkOptions(mode=BulkOperationMode.CONTINUE_ON_ERROR)
        result = self.bulk_manager.bulk_delete_events(
            calendar_uid="cal123", event_uids=self.test_uids, options=options
        )

        assert result.total == 3
        assert result.successful == 2
        assert result.failed == 1

        # Check that the failed operation has error info
        failures = result.get_failures()
        assert len(failures) == 1
        assert "Event not found" in failures[0].error
