"""
Tests for configuration validation
"""

import os
from unittest.mock import patch, Mock
import pytest

from chronos_mcp.config import ConfigManager
from chronos_mcp.exceptions import ValidationError


class TestConfigValidation:
    """Test configuration input validation"""

    @patch('os.getenv')
    @patch('chronos_mcp.config.get_credential_manager')
    def test_environment_password_validation(self, mock_cred_manager, mock_getenv):
        """Test that environment variable passwords are validated"""
        # Mock environment variables with control character in password
        def getenv_side_effect(key, default=None):
            env_vars = {
                'CALDAV_BASE_URL': 'https://example.com',
                'CALDAV_USERNAME': 'valid_user',
                'CALDAV_PASSWORD': 'a' * 11000  # Exceeds max length
            }
            return env_vars.get(key, default)

        mock_getenv.side_effect = getenv_side_effect
        mock_cred_manager.return_value.keyring_available = False

        # Should skip environment account due to validation failure
        config_mgr = ConfigManager()

        # Default account should not be created due to validation failure
        assert "default" not in config_mgr.config.accounts

    @patch('os.getenv')
    @patch('chronos_mcp.config.get_credential_manager')
    def test_environment_username_validation(self, mock_cred_manager, mock_getenv):
        """Test that environment variable usernames are validated"""
        # Mock environment variables with XSS in username
        def getenv_side_effect(key, default=None):
            env_vars = {
                'CALDAV_BASE_URL': 'https://example.com',
                'CALDAV_USERNAME': '<script>alert("xss")</script>',  # XSS - should be rejected
                'CALDAV_PASSWORD': 'ValidPassword123'
            }
            return env_vars.get(key, default)

        mock_getenv.side_effect = getenv_side_effect
        mock_cred_manager.return_value.keyring_available = False

        # Should skip environment account due to validation failure
        config_mgr = ConfigManager()

        # Default account should not be created
        assert "default" not in config_mgr.config.accounts

    @patch.dict(os.environ, {
        'CALDAV_BASE_URL': 'https://example.com',
        'CALDAV_USERNAME': 'valid_user',
        'CALDAV_PASSWORD': 'ValidP@ssw0rd!'
    })
    @patch('chronos_mcp.config.get_credential_manager')
    def test_environment_valid_credentials(self, mock_cred_manager):
        """Test that valid environment credentials are accepted"""
        mock_cred_mgr = Mock()
        mock_cred_mgr.keyring_available = False
        mock_cred_manager.return_value = mock_cred_mgr
        
        config_mgr = ConfigManager()
        
        # Default account should be created with valid inputs
        assert "default" in config_mgr.config.accounts
        assert config_mgr.config.accounts["default"].username == "valid_user"
        assert config_mgr.config.accounts["default"].password == "ValidP@ssw0rd!"
