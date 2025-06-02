"""
DevRev Get Object Tool

Provides a tool for fetching DevRev objects by ID.
"""

import json
from fastmcp import Context
from ..utils import make_devrev_request
from ..error_handler import tool_error_handler
from ..endpoints import WORKS_GET


@tool_error_handler("get_object")
async def get_object(id: str, ctx: Context, devrev_cache: dict) -> str:
    """
    Get all information about a DevRev issue and ticket using its ID.
    
    Args:
        id: The DevRev object ID
        ctx: FastMCP context
        devrev_cache: Cache dictionary for storing results
    
    Returns:
        JSON string containing the object information
    """
    try:
        await ctx.info(f"Fetching object {id} from DevRev")
        
        response = make_devrev_request(WORKS_GET, {"id": id})
        
        if response.status_code != 200:
            error_text = response.text
            await ctx.error(f"Failed to get object {id}: HTTP {response.status_code} - {error_text}")
            raise ValueError(f"Failed to get object {id} (HTTP {response.status_code}): {error_text}")
        
        result_data = response.json()
        
        # Cache the result
        devrev_cache[id] = json.dumps(result_data, indent=2)
        
        await ctx.info(f"Successfully retrieved object: {id}")
        return devrev_cache[id]
        
    except Exception as e:
        await ctx.error(f"Failed to get object {id}: {str(e)}")
        raise