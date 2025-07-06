"""
Shared logging configuration for Chronos MCP
"""

import sys
import logging

def setup_logging():
    """Configure logging to stderr for all Chronos modules"""
    # Only configure if not already configured
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            stream=sys.stderr,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Return logger for the calling module
    import inspect
    frame = inspect.stack()[1]
    module = inspect.getmodule(frame[0])
    return logging.getLogger(module.__name__ if module else __name__)
