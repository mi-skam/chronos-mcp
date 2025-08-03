"""
Account management for Chronos MCP
"""

import threading
import time
import uuid
from typing import Dict, Optional

import caldav
from caldav import DAVClient, Principal

from .config import ConfigManager
from .credentials import get_credential_manager
from .exceptions import (AccountAuthenticationError, AccountConnectionError,
                         AccountNotFoundError, ChronosError, ErrorHandler,
                         ErrorSanitizer)
from .logging_config import setup_logging
from .models import AccountStatus

logger = setup_logging()


class AccountManager:
    """Manage CalDAV account connections with lifecycle management"""

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.connections: Dict[str, DAVClient] = {}
        self.principals: Dict[str, Principal] = {}
        self._connection_locks: Dict[str, threading.Lock] = {}
        self._connection_timestamps: Dict[str, float] = {}
        self._connection_ttl_minutes: int = 30  # Connection TTL in minutes

    def connect_account(self, alias: str, request_id: Optional[str] = None) -> bool:
        """Connect to a CalDAV account - raises exceptions on failure"""
        request_id = request_id or str(uuid.uuid4())

        account = self.config.get_account(alias)
        if not account:
            raise AccountNotFoundError(alias, request_id=request_id)

        # Get password from keyring or fallback to config
        credential_manager = get_credential_manager()
        password = credential_manager.get_password(
            alias, fallback_password=account.password
        )

        if not password:
            raise AccountAuthenticationError(alias, request_id=request_id)

        try:
            client = DAVClient(
                url=str(account.url), username=account.username, password=password
            )

            # Test connection by getting principal
            principal = client.principal()

            # Store connection with timestamp
            self.connections[alias] = client
            self.principals[alias] = principal
            self._connection_timestamps[alias] = time.time()

            # Ensure lock exists for this connection
            if alias not in self._connection_locks:
                self._connection_locks[alias] = threading.Lock()

            account.status = AccountStatus.CONNECTED
            logger.info(
                f"Successfully connected to account '{alias}'",
                extra={"request_id": request_id},
            )
            return True

        except caldav.lib.error.AuthorizationError as e:
            account.status = AccountStatus.ERROR
            logger.error(
                f"Authentication failed for '{alias}': {e}",
                extra={"request_id": request_id},
            )
            raise AccountAuthenticationError(alias, request_id=request_id)
        except Exception as e:
            account.status = AccountStatus.ERROR
            logger.error(
                f"Failed to connect to account '{alias}': {e}",
                extra={"request_id": request_id},
            )
            raise AccountConnectionError(alias, original_error=e, request_id=request_id)

    def disconnect_account(self, alias: str):
        """Disconnect from an account and clean up resources"""
        if alias in self.connections:
            del self.connections[alias]
        if alias in self.principals:
            del self.principals[alias]
        if alias in self._connection_timestamps:
            del self._connection_timestamps[alias]
        if alias in self._connection_locks:
            del self._connection_locks[alias]

        account = self.config.get_account(alias)
        if account:
            account.status = AccountStatus.DISCONNECTED

        logger.debug(f"Disconnected and cleaned up resources for account '{alias}'")

    def cleanup_stale_connections(self, max_age_minutes: Optional[int] = None):
        """Remove connections older than max_age_minutes"""
        max_age = max_age_minutes or self._connection_ttl_minutes
        current_time = time.time()
        stale_aliases = []

        for alias, timestamp in self._connection_timestamps.items():
            age_minutes = (current_time - timestamp) / 60
            if age_minutes > max_age:
                stale_aliases.append(alias)

        for alias in stale_aliases:
            logger.debug(
                f"Cleaning up stale connection for account '{alias}' (age: {age_minutes:.1f} minutes)"
            )
            self.disconnect_account(alias)

        if stale_aliases:
            logger.info(f"Cleaned up {len(stale_aliases)} stale connections")

    def _is_connection_stale(self, alias: str) -> bool:
        """Check if a connection is stale"""
        if alias not in self._connection_timestamps:
            return True

        age_minutes = (time.time() - self._connection_timestamps[alias]) / 60
        return age_minutes > self._connection_ttl_minutes

    @ErrorHandler.safe_operation(logger, default_return=None)
    def get_connection(self, alias: Optional[str] = None) -> Optional[DAVClient]:
        """Get connection for an account - internal utility method"""
        if not alias:
            alias = self.config.config.default_account

        if alias and (
            alias not in self.connections or self._is_connection_stale(alias)
        ):
            # Clean up stale connection if it exists
            if alias in self.connections and self._is_connection_stale(alias):
                logger.debug(f"Connection for '{alias}' is stale, reconnecting")
                self.disconnect_account(alias)

            # Use thread lock to prevent race conditions in connection creation
            if alias not in self._connection_locks:
                self._connection_locks[alias] = threading.Lock()

            with self._connection_locks[alias]:
                # Double-check pattern - connection might have been created by another thread
                if alias not in self.connections:
                    self.connect_account(alias)

        return self.connections.get(alias) if alias else None

    @ErrorHandler.safe_operation(logger, default_return=None)
    def get_principal(self, alias: Optional[str] = None) -> Optional[Principal]:
        """Get principal for an account - internal utility method"""
        if not alias:
            alias = self.config.config.default_account

        if alias and (alias not in self.principals or self._is_connection_stale(alias)):
            # Clean up stale connection if it exists
            if alias in self.principals and self._is_connection_stale(alias):
                logger.debug(f"Principal for '{alias}' is stale, reconnecting")
                self.disconnect_account(alias)

            # Use thread lock to prevent race conditions in connection creation
            if alias not in self._connection_locks:
                self._connection_locks[alias] = threading.Lock()

            with self._connection_locks[alias]:
                # Double-check pattern - connection might have been created by another thread
                if alias not in self.principals:
                    self.connect_account(alias)

        return self.principals.get(alias) if alias else None

    def test_account(
        self, alias: str, request_id: Optional[str] = None
    ) -> Dict[str, any]:
        """Test account connectivity and return structured result"""
        result = {"alias": alias, "connected": False, "calendars": 0, "error": None}

        request_id = request_id or str(uuid.uuid4())

        try:
            if self.connect_account(alias, request_id=request_id):
                principal = self.principals.get(alias)
                if principal:
                    calendars = principal.calendars()
                    result["connected"] = True
                    result["calendars"] = len(calendars)
        except ChronosError as e:
            # Use sanitized error message for user response
            result["error"] = ErrorSanitizer.get_user_friendly_message(e)
            logger.error(f"Test account failed: {e}", extra={"request_id": request_id})
        except Exception as e:
            # Unexpected error - wrap and sanitize
            wrapped_error = AccountConnectionError(
                alias, original_error=e, request_id=request_id
            )
            result["error"] = ErrorSanitizer.get_user_friendly_message(wrapped_error)
            logger.error(
                f"Test account failed with unexpected error: {wrapped_error}",
                extra={"request_id": request_id},
            )

        return result
