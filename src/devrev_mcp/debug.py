"""
Debug utilities for DevRev MCP server.
"""

import traceback
import os
from functools import wraps
from typing import Dict, Any, List

import mcp.types as types

# Check debug mode and store state
DEBUG_ENABLED = os.environ.get("DRMCP_DEBUG") == "1"
DEBUG_MESSAGE = "🐛 DEBUG MODE ENABLED - sara wuz here" if DEBUG_ENABLED else "🐛 DEBUG MODE DISABLED - sara wuz here"

def debug_error_handler(func):
    """
    Decorator that catches exceptions in MCP functions and returns detailed debug information
    as the response when DRMCP_DEBUG=1.
    """
    debug_enabled = DEBUG_ENABLED
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            # Add debug message to all responses when debug is enabled
            if debug_enabled and result:
                # For tool responses (list of content)
                if isinstance(result, list) and len(result) > 0 and hasattr(result[0], 'text'):
                    debug_content = types.TextContent(
                        type="text", 
                        text=f"{DEBUG_MESSAGE}\n\n"
                    )
                    result[0].text = debug_content.text + result[0].text
                # For other responses (strings, etc.) - just add debug message
                elif isinstance(result, str) and debug_enabled:
                    result = f"{DEBUG_MESSAGE}\n\n{result}"
            return result
        except Exception as e:
            if debug_enabled:
                # Debug mode: return detailed error information
                error_message = f"""ERROR (Debug Mode): {type(e).__name__}: {str(e)}

Full traceback:
{traceback.format_exc()}

This is a debug error response. Let's troubleshoot this together.

{DEBUG_MESSAGE}"""
            else:
                # Production mode: return generic error message
                error_message = f"An error occurred while executing the function. Please try again or contact support."
            
            # Return appropriate error format based on expected return type
            if hasattr(func, '__annotations__') and func.__annotations__.get('return'):
                return_type = func.__annotations__['return']
                if 'List' in str(return_type) and 'TextContent' in str(return_type):
                    # Tool function - return list of TextContent
                    return [
                        types.TextContent(
                            type="text",
                            text=error_message
                        )
                    ]
            
            # Default: return as string (for resource handlers, etc.)
            return error_message
    
    return wrapper 