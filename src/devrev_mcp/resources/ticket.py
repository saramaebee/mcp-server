"""
DevRev Ticket Resource Handler

Provides specialized resource access for DevRev tickets with enriched timeline and artifact data.
"""

import json
from fastmcp import Context
from ..utils import make_devrev_request, normalize_ticket_id
from ..error_handler import resource_error_handler
from ..endpoints import WORKS_GET, TIMELINE_ENTRIES_LIST


@resource_error_handler("ticket")
async def ticket(ticket_id: str, ctx: Context, devrev_cache: dict) -> str:
    """
    Access DevRev ticket details with enriched timeline entries and artifact data.
    
    Args:
        ticket_id: The DevRev ticket ID (e.g., 12345 for TKT-12345)
        ctx: FastMCP context
        devrev_cache: Cache dictionary for storing results
    
    Returns:
        JSON string containing the ticket data with timeline entries and artifacts
    """
    # Normalize ticket ID for API calls
    normalized_id = normalize_ticket_id(ticket_id)
    cache_key = f"devrev://tickets/{ticket_id}"
    
    # Check cache first
    cached_value = devrev_cache.get(cache_key)
    if cached_value is not None:
        await ctx.info(f"Retrieved ticket {normalized_id} from cache")
        return cached_value
    
    await ctx.info(f"Fetching ticket {normalized_id} from DevRev API")
    
    # Get ticket details
    response = make_devrev_request(WORKS_GET, {"id": normalized_id})
    
    if response.status_code != 200:
        error_text = response.text
        await ctx.error(f"Failed to fetch ticket {normalized_id}: HTTP {response.status_code} - {error_text}")
        raise ValueError(f"Failed to fetch ticket {normalized_id} (HTTP {response.status_code}): {error_text}")
    
    result = response.json()
    
    # Extract the work object from the API response
    if isinstance(result, dict) and "work" in result:
        result = result["work"]
    
    # Get timeline entries for the ticket
    try:
        timeline_response = make_devrev_request(
            TIMELINE_ENTRIES_LIST,
            {"object": normalized_id}
        )
        
        if timeline_response.status_code == 200:
            timeline_data = timeline_response.json()
            timeline_entries = timeline_data.get("timeline_entries", [])
            result["timeline_entries"] = timeline_entries
            await ctx.info(f"Added {len(timeline_entries)} timeline entries to ticket {normalized_id}")
            
            # Extract artifact data directly from timeline entries (no additional API calls needed)
            artifacts = []
            seen_artifact_ids = set()  # Avoid duplicates across timeline entries
            
            for entry in timeline_entries:
                if "artifacts" in entry:
                    for artifact in entry["artifacts"]:
                        # Timeline entries contain full artifact objects, not just IDs
                        if isinstance(artifact, dict):
                            artifact_id = artifact.get("id", "")
                            if artifact_id and artifact_id not in seen_artifact_ids:
                                seen_artifact_ids.add(artifact_id)
                                
                                # Add navigation link for downloading
                                artifact_id_clean = artifact_id.split("/")[-1] if "/" in artifact_id else artifact_id
                                artifact["links"] = {
                                    "download": f"devrev://artifacts/{artifact_id_clean}/download",
                                    "ticket": f"devrev://tickets/{ticket_id}"
                                }
                                artifacts.append(artifact)
                        elif isinstance(artifact, str):
                            # Fallback: if it's just an ID string, create minimal artifact object
                            if artifact not in seen_artifact_ids:
                                seen_artifact_ids.add(artifact)
                                artifact_id_clean = artifact.split("/")[-1] if "/" in artifact else artifact
                                artifacts.append({
                                    "id": artifact,
                                    "links": {
                                        "download": f"devrev://artifacts/{artifact_id_clean}/download",
                                        "ticket": f"devrev://tickets/{ticket_id}"
                                    }
                                })
            
            result["artifacts"] = artifacts
            await ctx.info(f"Extracted {len(artifacts)} artifacts from timeline entries for ticket {normalized_id}")
            
        else:
            await ctx.warning(f"Could not fetch timeline entries for ticket {normalized_id}")
            result["timeline_entries"] = []
            result["artifacts"] = []
    except Exception as e:
        await ctx.warning(f"Error fetching timeline entries for ticket {normalized_id}: {str(e)}")
        result["timeline_entries"] = []
        result["artifacts"] = []
    
    # Add navigation links
    result["links"] = {
        "timeline": f"devrev://tickets/{ticket_id}/timeline",
        "artifacts": f"devrev://tickets/{ticket_id}/artifacts"
    }
    
    # Cache the enriched result
    cache_value = json.dumps(result, indent=2)
    devrev_cache.set(cache_key, cache_value)
    await ctx.info(f"Successfully retrieved and cached ticket: {normalized_id}")
    
    return cache_value