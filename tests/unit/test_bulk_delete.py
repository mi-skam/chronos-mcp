"""
Unit tests for bulk event deletion functionality
"""
import pytest
from unittest.mock import Mock, patch, call
from chronos_mcp.server import bulk_delete_events
from chronos_mcp.exceptions import ChronosError, EventNotFoundError


class TestBulkDeleteEvents:
    """Test the bulk_delete_events function"""
    
    @pytest.fixture
    def mock_managers(self):
        """Setup mock managers"""
        with patch('chronos_mcp.server.event_manager') as mock_event, \
             patch('chronos_mcp.server.logger') as mock_logger:
            yield {
                'event': mock_event,
                'logger': mock_logger
            }
    
    @pytest.fixture
    def event_uids(self):
        """Sample event UIDs for testing"""
        return [
            "uid-1",
            "uid-2",
            "uid-3",
            "uid-4",
            "uid-5"
        ]
    
    @pytest.mark.asyncio
    async def test_bulk_delete_success(self, mock_managers, event_uids):
        """Test successful bulk deletion"""
        # Mock successful deletions
        mock_managers['event'].delete_event.return_value = None
        
        result = await bulk_delete_events(
            calendar_uid="test-cal",
            event_uids=event_uids,
            mode="continue"
        )
        
        assert result['success'] is True
        assert result['total'] == 5
        assert result['succeeded'] == 5
        assert result['failed'] == 0
        assert len(result['details']) == 5
        
        # Check all were successful
        for detail in result['details']:
            assert detail['success'] is True
            assert 'error' not in detail
        
        # Verify all delete calls were made
        assert mock_managers['event'].delete_event.call_count == 5
    
    @pytest.mark.asyncio
    async def test_bulk_delete_continue_mode(self, mock_managers, event_uids):
        """Test continue mode with partial failures"""
        # Mock mixed success/failure
        def delete_side_effect(*args, **kwargs):
            uid = kwargs.get('event_uid')
            if uid in ["uid-2", "uid-4"]:
                raise EventNotFoundError(
                    event_uid=uid,
                    calendar_uid=kwargs.get('calendar_uid')
                )
            return None
        
        mock_managers['event'].delete_event.side_effect = delete_side_effect
        
        result = await bulk_delete_events(
            calendar_uid="test-cal",
            event_uids=event_uids,
            mode="continue"
        )
        
        assert result['success'] is False
        assert result['total'] == 5
        assert result['succeeded'] == 3
        assert result['failed'] == 2
        
        # Check failed events
        failed_details = [d for d in result['details'] if not d['success']]
        assert len(failed_details) == 2
        assert failed_details[0]['uid'] == "uid-2"
        assert "EventNotFoundError" in failed_details[0]['error']
    
    @pytest.mark.asyncio
    async def test_bulk_delete_fail_fast_mode(self, mock_managers, event_uids):
        """Test fail_fast mode stops on first error"""
        # Mock failure on third event
        def delete_side_effect(*args, **kwargs):
            uid = kwargs.get('event_uid')
            if uid == "uid-3":
                raise EventNotFoundError(
                    event_uid=uid,
                    calendar_uid=kwargs.get('calendar_uid')
                )
            return None
        
        mock_managers['event'].delete_event.side_effect = delete_side_effect
        
        result = await bulk_delete_events(
            calendar_uid="test-cal",
            event_uids=event_uids,
            mode="fail_fast"
        )
        
        assert result['success'] is False
        assert result['total'] == 5
        assert result['succeeded'] == 2
        assert result['failed'] == 1
        assert len(result['details']) == 3  # Stopped after failure
        
        # Only 3 delete calls should have been made
        assert mock_managers['event'].delete_event.call_count == 3
    
    @pytest.mark.asyncio
    async def test_bulk_delete_invalid_mode(self, mock_managers, event_uids):
        """Test invalid mode validation"""
        result = await bulk_delete_events(
            calendar_uid="test-cal",
            event_uids=event_uids,
            mode="atomic"  # Invalid mode
        )
        
        assert result['success'] is False
        assert "Invalid mode" in result['error']
        assert result['error_code'] == "VALIDATION_ERROR"
    
    @pytest.mark.asyncio
    async def test_bulk_delete_empty_list(self, mock_managers):
        """Test empty UID list"""
        result = await bulk_delete_events(
            calendar_uid="test-cal",
            event_uids=[],
            mode="continue"
        )
        
        assert result['success'] is True
        assert result['total'] == 0
        assert result['succeeded'] == 0
        assert result['failed'] == 0
        assert len(result['details']) == 0
        
        # No delete calls should have been made
        mock_managers['event'].delete_event.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_bulk_delete_with_account(self, mock_managers):
        """Test deletion with account parameter"""
        mock_managers['event'].delete_event.return_value = None
        
        result = await bulk_delete_events(
            calendar_uid="test-cal",
            event_uids=["uid-1"],
            mode="continue",
            account="test-account"
        )
        
        assert result['success'] is True
        
        # Check account was passed correctly
        call_args = mock_managers['event'].delete_event.call_args[1]
        assert call_args['account_alias'] == "test-account"
    
    @pytest.mark.asyncio
    async def test_bulk_delete_request_id_propagation(self, mock_managers):
        """Test request_id is properly propagated"""
        mock_managers['event'].delete_event.return_value = None
        
        result = await bulk_delete_events(
            calendar_uid="test-cal",
            event_uids=["uid-1", "uid-2"],
            mode="continue"
        )
        
        assert 'request_id' in result
        
        # Check request_id was passed to all delete calls
        for call in mock_managers['event'].delete_event.call_args_list:
            assert 'request_id' in call[1]
            assert call[1]['request_id'] == result['request_id']
    
    @pytest.mark.asyncio
    async def test_bulk_delete_generic_error_handling(self, mock_managers):
        """Test handling of non-ChronosError exceptions"""
        # Mock generic exception
        mock_managers['event'].delete_event.side_effect = Exception("Network error")
        
        result = await bulk_delete_events(
            calendar_uid="test-cal",
            event_uids=["uid-1"],
            mode="continue"
        )
        
        assert result['success'] is False
        assert result['failed'] == 1
        assert "Network error" in result['details'][0]['error']
    
    @pytest.mark.asyncio
    async def test_bulk_delete_all_fail(self, mock_managers):
        """Test when all deletions fail"""
        mock_managers['event'].delete_event.side_effect = EventNotFoundError(
            event_uid="any",
            calendar_uid="test-cal"
        )
        
        result = await bulk_delete_events(
            calendar_uid="test-cal",
            event_uids=["uid-1", "uid-2", "uid-3"],
            mode="continue"
        )
        
        assert result['success'] is False
        assert result['succeeded'] == 0
        assert result['failed'] == 3
        assert all(not d['success'] for d in result['details'])
    
    @pytest.mark.asyncio
    async def test_bulk_delete_duplicate_uids(self, mock_managers):
        """Test handling of duplicate UIDs"""
        mock_managers['event'].delete_event.return_value = None
        
        # Include duplicate UIDs
        uids_with_dupes = ["uid-1", "uid-2", "uid-1", "uid-3", "uid-2"]
        
        result = await bulk_delete_events(
            calendar_uid="test-cal",
            event_uids=uids_with_dupes,
            mode="continue"
        )
        
        # Should process all UIDs including duplicates
        assert result['total'] == 5
        assert mock_managers['event'].delete_event.call_count == 5
