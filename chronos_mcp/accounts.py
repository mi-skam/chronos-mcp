"""
Account management for Chronos MCP
"""

import sys
import uuid
from typing import Dict, List, Optional
import caldav
from caldav import DAVClient, Principal

from .models import Account, AccountStatus
from .config import ConfigManager
from .credentials import get_credential_manager
from .logging_config import setup_logging
from .exceptions import (
    AccountNotFoundError,
    AccountConnectionError,
    AccountAuthenticationError,
    AccountAlreadyExistsError,
    ChronosError,
    ErrorHandler,
    ErrorSanitizer
)

# Set up logging
logger = setup_logging()


class AccountManager:
    """Manage CalDAV account connections"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.connections: Dict[str, DAVClient] = {}
        self.principals: Dict[str, Principal] = {}

        
    def connect_account(self, alias: str, request_id: Optional[str] = None) -> bool:
        """Connect to a CalDAV account - raises exceptions on failure"""
        request_id = request_id or str(uuid.uuid4())
        
        account = self.config.get_account(alias)
        if not account:
            raise AccountNotFoundError(alias, request_id=request_id)
            
        # Get password from keyring or fallback to config
        credential_manager = get_credential_manager()
        password = credential_manager.get_password(alias, fallback_password=account.password)
        
        if not password:
            raise AccountAuthenticationError(
                alias,
                request_id=request_id
            )
            
        try:
            client = DAVClient(
                url=str(account.url),
                username=account.username,
                password=password
            )
            
            # Test connection by getting principal
            principal = client.principal()
            
            # Store connection
            self.connections[alias] = client
            self.principals[alias] = principal
            
            # Update account status
            account.status = AccountStatus.CONNECTED
            logger.info(f"Successfully connected to account '{alias}'", extra={"request_id": request_id})
            return True
            
        except caldav.lib.error.AuthorizationError as e:
            account.status = AccountStatus.ERROR
            logger.error(f"Authentication failed for '{alias}': {e}", extra={"request_id": request_id})
            raise AccountAuthenticationError(alias, request_id=request_id)
        except Exception as e:
            account.status = AccountStatus.ERROR
            logger.error(f"Failed to connect to account '{alias}': {e}", extra={"request_id": request_id})
            raise AccountConnectionError(alias, original_error=e, request_id=request_id)

            
    def disconnect_account(self, alias: str):
        """Disconnect from an account"""
        if alias in self.connections:
            del self.connections[alias]
        if alias in self.principals:
            del self.principals[alias]
            
        account = self.config.get_account(alias)
        if account:
            account.status = AccountStatus.DISCONNECTED
            
    @ErrorHandler.safe_operation(logger, default_return=None)
    def get_connection(self, alias: Optional[str] = None) -> Optional[DAVClient]:
        """Get connection for an account - internal utility method"""
        if not alias:
            alias = self.config.config.default_account
            
        if alias and alias not in self.connections:
            # Try to connect if not already connected
            self.connect_account(alias)
            
        return self.connections.get(alias) if alias else None
        
    @ErrorHandler.safe_operation(logger, default_return=None)  
    def get_principal(self, alias: Optional[str] = None) -> Optional[Principal]:
        """Get principal for an account - internal utility method"""
        if not alias:
            alias = self.config.config.default_account
            
        if alias and alias not in self.principals:
            # Try to connect if not already connected
            self.connect_account(alias)
            
        return self.principals.get(alias) if alias else None
        
    def test_account(self, alias: str, request_id: Optional[str] = None) -> Dict[str, any]:
        """Test account connectivity and return structured result"""
        result = {
            "alias": alias,
            "connected": False,
            "calendars": 0,
            "error": None
        }
        
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
            wrapped_error = AccountConnectionError(alias, original_error=e, request_id=request_id)
            result["error"] = ErrorSanitizer.get_user_friendly_message(wrapped_error)
            logger.error(f"Test account failed with unexpected error: {wrapped_error}", extra={"request_id": request_id})
            
        return result
