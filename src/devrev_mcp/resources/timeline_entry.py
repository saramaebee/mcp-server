"""
DevRev Timeline Entry Resource Handler

Provides specialized resource access for DevRev timeline entries with conversation data.
"""

import json
from fastmcp import Context
from ..utils import make_devrev_request
from ..debug import debug_error_handler


@debug_error_handler
async def timeline_entry(timeline_id: str, ctx: Context, devrev_cache: dict) -> str:
    """
    Access specific timeline entry details.
    
    Args:
        timeline_id: The DevRev timeline entry ID (full don: format)
        ctx: FastMCP context
        devrev_cache: Cache dictionary for storing results
    
    Returns:
        JSON string containing the timeline entry data
    """
    try:
        cache_key = f"timeline:{timeline_id}"
        
        # Check cache first
        if cache_key in devrev_cache:
            await ctx.info(f"Retrieved timeline entry {timeline_id} from cache")
            return devrev_cache[cache_key]
        
        await ctx.info(f"Fetching timeline entry {timeline_id} from DevRev API")
        
        # For timeline entries, use timeline-entries.get endpoint
        response = make_devrev_request(
            "timeline-entries.get",
            {"id": timeline_id}
        )
        
        if response.status_code != 200:
            error_text = response.text
            await ctx.error(f"Failed to fetch timeline entry {timeline_id}: HTTP {response.status_code} - {error_text}")
            raise ValueError(f"Failed to fetch timeline entry {timeline_id} (HTTP {response.status_code}): {error_text}")
        
        result = response.json()
        
        # Add navigation links
        # Extract ticket ID from the timeline entry if available
        ticket_id = None
        if "object" in result:
            object_id = result["object"]
            if "TKT-" in object_id:
                ticket_id = object_id.replace("TKT-", "")
        
        links = {}
        if ticket_id:
            links["ticket"] = f"devrev://tickets/{ticket_id}"
            links["ticket_timeline"] = f"devrev://tickets/{ticket_id}/timeline"
        
        # Add links to artifacts if any are attached
        if "artifacts" in result and result["artifacts"]:
            links["artifacts"] = [f"devrev://artifacts/{artifact_id}" for artifact_id in result["artifacts"]]
        
        result["links"] = links
        
        # Cache the result
        devrev_cache[cache_key] = json.dumps(result, indent=2)
        await ctx.info(f"Successfully retrieved and cached timeline entry: {timeline_id}")
        
        return devrev_cache[cache_key]
        
    except Exception as e:
        await ctx.error(f"Failed to get timeline resource {timeline_id}: {str(e)}")
        raise ValueError(f"Timeline resource {timeline_id} not found: {str(e)}")