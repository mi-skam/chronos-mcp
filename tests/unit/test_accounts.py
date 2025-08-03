"""
Unit tests for account management
"""

import time
from unittest.mock import Mock, patch

import pytest
from caldav.lib.error import AuthorizationError

from chronos_mcp.accounts import AccountManager
from chronos_mcp.exceptions import (AccountAuthenticationError,
                                    AccountNotFoundError)
from chronos_mcp.models import AccountStatus


class TestAccountManager:
    def test_init(self, mock_config_manager):
        """Test AccountManager initialization"""
        mgr = AccountManager(mock_config_manager)
        assert mgr.config == mock_config_manager
        assert mgr.connections == {}
        assert mgr.principals == {}

    def test_connect_account_not_found(self, mock_config_manager):
        """Test connecting to non-existent account"""
        # Use real config manager - account doesn't exist
        mgr = AccountManager(mock_config_manager)

        # Should raise AccountNotFoundError
        with pytest.raises(AccountNotFoundError) as exc_info:
            mgr.connect_account("nonexistent")

        assert "nonexistent" in str(exc_info.value)
        assert exc_info.value.details["alias"] == "nonexistent"

    @patch("chronos_mcp.accounts.DAVClient")
    def test_connect_account_success(
        self, mock_dav_client, mock_config_manager, sample_account
    ):
        """Test successful connection to an account"""
        # Add account to config manager first
        mock_config_manager.add_account(sample_account)
        mgr = AccountManager(mock_config_manager)

        # Mock successful connection
        mock_client = Mock()
        mock_dav_client.return_value = mock_client
        mock_principal = Mock()
        mock_client.principal.return_value = mock_principal

        result = mgr.connect_account("test_account")
        assert result is True
        assert "test_account" in mgr.connections
        assert "test_account" in mgr.principals
        assert sample_account.status == AccountStatus.CONNECTED

    @patch("chronos_mcp.accounts.DAVClient")
    def test_connect_account_failure(
        self, mock_dav_client, mock_config_manager, sample_account
    ):
        """Test connection failure"""
        # Add account to config manager first
        mock_config_manager.add_account(sample_account)
        mgr = AccountManager(mock_config_manager)

        # Mock connection failure
        mock_dav_client.side_effect = AuthorizationError("Invalid credentials")

        # Should raise AccountAuthenticationError
        with pytest.raises(AccountAuthenticationError) as exc_info:
            mgr.connect_account("test_account")

        assert exc_info.value.details["alias"] == "test_account"
        assert sample_account.status == AccountStatus.ERROR

    def test_disconnect_account(self, mock_config_manager, sample_account):
        """Test disconnecting an account"""
        # Add account to config manager first
        mock_config_manager.add_account(sample_account)
        mgr = AccountManager(mock_config_manager)

        # Simulate connected account
        mgr.connections["test_account"] = Mock()
        mgr.principals["test_account"] = Mock()

        mgr.disconnect_account("test_account")
        assert "test_account" not in mgr.connections
        assert "test_account" not in mgr.principals
        assert sample_account.status == AccountStatus.DISCONNECTED

    def test_get_connection_not_connected(self, mock_config_manager, sample_account):
        """Test getting connection when not connected - should auto-connect"""
        mock_config_manager.config.default_account = None
        mock_config_manager.add_account(sample_account)
        mgr = AccountManager(mock_config_manager)

        # Mock connect_account to fail
        with patch.object(mgr, "connect_account", return_value=False):
            connection = mgr.get_connection("test_account")
            assert connection is None

    @patch("chronos_mcp.accounts.DAVClient")
    def test_test_account(self, mock_dav_client, mock_config_manager, sample_account):
        """Test testing account connectivity"""
        # Add account to config manager first
        mock_config_manager.add_account(sample_account)
        mgr = AccountManager(mock_config_manager)

        # Mock successful connection
        mock_client = Mock()
        mock_dav_client.return_value = mock_client
        mock_principal = Mock()
        mock_client.principal.return_value = mock_principal
        mock_calendars = [Mock(), Mock()]
        mock_principal.calendars.return_value = mock_calendars

        result = mgr.test_account("test_account")
        assert result["alias"] == "test_account"
        assert result["connected"] is True
        assert result["calendars"] == 2
        assert result["error"] is None

    def test_get_principal(self, mock_config_manager):
        """Test getting principal for an account"""
        mgr = AccountManager(mock_config_manager)

        # No principal when not connected
        principal = mgr.get_principal("nonexistent")
        assert principal is None

        # Should return principal when connected
        mock_principal = Mock()
        mgr.principals["test_account"] = mock_principal
        # Add timestamp to prevent stale connection check
        mgr._connection_timestamps["test_account"] = time.time()

        principal = mgr.get_principal("test_account")
        assert principal == mock_principal

    @patch("chronos_mcp.accounts.DAVClient")
    def test_get_connection_with_default(
        self, mock_dav_client, mock_config_manager, sample_account
    ):
        """Test getting connection uses default account when no alias provided"""
        # Set up default account
        mock_config_manager.add_account(sample_account)
        mock_config_manager.config.default_account = "test_account"

        mgr = AccountManager(mock_config_manager)

        # Mock successful connection
        mock_client = Mock()
        mock_dav_client.return_value = mock_client
        mock_principal = Mock()
        mock_client.principal.return_value = mock_principal

        # Get connection without specifying alias
        connection = mgr.get_connection()

        # Should have connected to default account
        assert "test_account" in mgr.connections
