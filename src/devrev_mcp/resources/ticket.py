"""
DevRev Ticket Resource Handler

Provides specialized resource access for DevRev tickets with enriched timeline and artifact data.
"""

import json
from fastmcp import Context
from ..utils import make_devrev_request


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
    try:
        await ctx.info(f"[DEBUG] ticket() called with ticket_id: {ticket_id}")
        
        # Convert simple ID to TKT- format for API calls
        if ticket_id.upper().startswith("TKT-"):
            # Extract numeric part and reformat
            numeric_id = ticket_id[4:]  # Remove TKT- or tkt-
            normalized_id = f"TKT-{numeric_id}"
        else:
            normalized_id = f"TKT-{ticket_id}"
        cache_key = f"ticket:{ticket_id}"
        
        await ctx.info(f"[DEBUG] normalized_id: {normalized_id}, cache_key: {cache_key}")
        
        # Check cache first
        if cache_key in devrev_cache:
            await ctx.info(f"Retrieved ticket {normalized_id} from cache")
            return devrev_cache[cache_key]
        
        await ctx.info(f"Fetching ticket {normalized_id} from DevRev API")
        
        # Get ticket details
        response = make_devrev_request("works.get", {"id": normalized_id})
        
        if response.status_code != 200:
            error_text = response.text
            await ctx.error(f"Failed to fetch ticket {normalized_id}: HTTP {response.status_code} - {error_text}")
            raise ValueError(f"Failed to fetch ticket {normalized_id} (HTTP {response.status_code}): {error_text}")
        
        result = response.json()
        await ctx.info(f"[DEBUG] API response structure: {list(result.keys()) if isinstance(result, dict) else type(result)}")
        
        # Extract the work object from the API response
        if isinstance(result, dict) and "work" in result:
            result = result["work"]
        
        # Get timeline entries for the ticket
        try:
            timeline_response = make_devrev_request(
                "timeline-entries.list",
                {"object": normalized_id}
            )
            
            if timeline_response.status_code == 200:
                timeline_data = timeline_response.json()
                timeline_entries = timeline_data.get("timeline_entries", [])
                result["timeline_entries"] = timeline_entries
                await ctx.info(f"Added {len(timeline_entries)} timeline entries to ticket {normalized_id}")
                
                # Extract and gather artifact data from timeline entries
                artifacts = []
                for entry in timeline_entries:
                    if "artifacts" in entry:
                        for artifact_id in entry["artifacts"]:
                            try:
                                artifact_response = make_devrev_request(
                                    "artifacts.get",
                                    {"id": artifact_id}
                                )
                                if artifact_response.status_code == 200:
                                    artifact_data = artifact_response.json()
                                    artifacts.append(artifact_data)
                            except Exception as e:
                                await ctx.warning(f"Could not fetch artifact {artifact_id}: {str(e)}")
                
                result["artifacts"] = artifacts
                await ctx.info(f"Added {len(artifacts)} artifacts to ticket {normalized_id}")
                
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
        devrev_cache[cache_key] = json.dumps(result, indent=2)
        await ctx.info(f"Successfully retrieved and cached ticket: {normalized_id}")
        
        return devrev_cache[cache_key]
        
    except Exception as e:
        await ctx.error(f"Failed to get ticket resource {ticket_id}: {str(e)}")
        # Return empty JSON object instead of raising exception
        return json.dumps({"error": f"Ticket resource {ticket_id} not found: {str(e)}"}, indent=2)