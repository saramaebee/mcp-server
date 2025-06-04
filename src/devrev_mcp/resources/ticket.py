"""
DevRev Ticket Resource Handler

Provides specialized resource access for DevRev tickets with enriched timeline and artifact data.
"""

import json
from fastmcp import Context
from ..utils import make_devrev_request, fetch_linked_work_items, read_resource_content
from ..error_handler import resource_error_handler
from ..endpoints import WORKS_GET, TIMELINE_ENTRIES_LIST


@resource_error_handler("ticket")
async def ticket(ticket_number: str, ctx: Context, devrev_cache: dict) -> str:
    """
    Access DevRev ticket details with enriched timeline entries and artifact data.
    
    Args:
        ticket_number: The numeric DevRev ticket ID (e.g., "12345")
        ctx: FastMCP context
        devrev_cache: Cache dictionary for storing results
    
    Returns:
        JSON string containing the ticket data with timeline entries and artifacts
    """
    # Use the display ID format that the API expects
    ticket_id = f"TKT-{ticket_number}"
    cache_key = f"devrev://tickets/{ticket_number}"
    
    # Check cache first
    cached_value = devrev_cache.get(cache_key)
    if cached_value is not None:
        await ctx.info(f"Retrieved ticket {ticket_number} from cache")
        return cached_value
    
    await ctx.info(f"Fetching ticket {ticket_id} from DevRev API")
    
    # Get ticket details using the display ID
    response = make_devrev_request(WORKS_GET, {"id": ticket_id})
    
    if response.status_code != 200:
        error_text = response.text
        await ctx.error(f"Failed to fetch ticket {ticket_id}: HTTP {response.status_code} - {error_text}")
        raise ValueError(f"Failed to fetch ticket {ticket_id} (HTTP {response.status_code}): {error_text}")
    
    result = response.json()
    
    # Extract the work object from the API response
    if isinstance(result, dict) and "work" in result:
        result = result["work"]
    
    # Get timeline entries for the ticket

    
    # Get linked work items using the reusable utility function
    work_item_don_id = result.get("id", ticket_id)  # Use the full don:core ID from the API response
    linked_work_items = await fetch_linked_work_items(
        work_item_id=work_item_don_id,
        work_item_display_id=ticket_id,
        work_item_type="ticket",
        ctx=ctx,
        cache=devrev_cache
    )
    
    # Add navigation links (artifacts are now directly included in the ticket data)
    result["links"] = {
        "timeline": await read_resource_content(ctx, f"devrev://tickets/{ticket_number}/timeline", parse_json=True), 
        "works": linked_work_items,
        "artifacts": await read_resource_content(ctx, f"devrev://tickets/{ticket_number}/artifacts", parse_json=True)
    }
    
    # Cache the enriched result
    cache_value = json.dumps(result, indent=2, default=str)
    devrev_cache.set(cache_key, cache_value)
    await ctx.info(f"Successfully retrieved and cached ticket: {ticket_number}")
    
    return cache_value