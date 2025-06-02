"""
DevRev Get Ticket Tool

Provides a tool for fetching DevRev tickets with enriched timeline entries and artifact data.
"""

import json
from fastmcp import Context
from ..error_handler import tool_error_handler


@tool_error_handler("get_ticket")
async def get_ticket(
    id: str,
    ctx: Context
) -> str:
    """
    Get a DevRev ticket with all associated timeline entries and artifacts.
    
    Args:
        id: The DevRev ticket ID - accepts TKT-12345, 12345, or full don:core format
        ctx: FastMCP context
    
    Returns:
        JSON string containing the ticket data with timeline entries and artifacts
    """
    try:
        # Normalize the ticket ID to just the number
        if id.upper().startswith("TKT-"):
            ticket_id = id[4:]  # Remove TKT- prefix
        elif id.startswith("don:core:"):
            # Extract ID from don:core format
            ticket_id = id.split(":")[-1]
        else:
            ticket_id = id

        await ctx.info(f"Fetching ticket {ticket_id} with timeline entries and artifacts")
        
        # Get the main ticket data
        ticket_uri = f"devrev://tickets/{ticket_id}"
        try:
            resource_contents = await ctx.read_resource(ticket_uri)
            
            if resource_contents and len(resource_contents) > 0:
                # Handle multiple contents by trying each until we find valid JSON
                if len(resource_contents) > 1:
                    await ctx.warning(f"Multiple resource contents returned ({len(resource_contents)}), trying each for valid JSON")
                
                ticket_data = None
                for i, content_item in enumerate(resource_contents):
                    try:
                        ticket_data = json.loads(content_item.content)
                        if i > 0:
                            await ctx.info(f"Successfully parsed JSON from content item {i}")
                        break
                    except json.JSONDecodeError as e:
                        await ctx.warning(f"Content item {i} is not valid JSON: {e}")
                        continue
                
                if ticket_data is None:
                    raise ValueError(f"No valid JSON found in any of the {len(resource_contents)} resource contents")
            else:
                raise ValueError(f"No resource contents returned for {ticket_uri}")
        except Exception as ticket_error:
            await ctx.error(f"Error reading ticket resource {ticket_uri}: {str(ticket_error)}")
            raise ticket_error

        if not ticket_data:
            return f"No ticket found with ID {ticket_id}"

        # Handle case where ticket_data is unexpectedly a list
        if isinstance(ticket_data, list):
            await ctx.warning(f"ticket_data is unexpectedly a list, using first item")
            if len(ticket_data) > 0:
                ticket_data = ticket_data[0]
            else:
                return f"No ticket data found for ID {ticket_id}"

        # Ensure ticket_data is a dict
        if not isinstance(ticket_data, dict):
            await ctx.error(f"ticket_data is not a dict, type: {type(ticket_data)}, value: {repr(ticket_data)}")
            return f"Invalid ticket data format for ID {ticket_id} (type: {type(ticket_data)})"

        # Get timeline entries
        timeline_uri = f"devrev://tickets/{ticket_id}/timeline"
        try:
            timeline_contents = await ctx.read_resource(timeline_uri)
            if timeline_contents and len(timeline_contents) > 0:
                # Try each content item for valid JSON
                timeline_data = None
                for i, content_item in enumerate(timeline_contents):
                    try:
                        timeline_data = json.loads(content_item.content)
                        break
                    except json.JSONDecodeError:
                        continue
                
                ticket_data["timeline_entries"] = timeline_data if timeline_data else []
            else:
                ticket_data["timeline_entries"] = []
        except Exception as timeline_error:
            await ctx.warning(f"Error reading timeline entries: {str(timeline_error)}")
            ticket_data["timeline_entries"] = []

        # Get artifacts if any are referenced
        artifacts = []
        if "artifact_uris" in ticket_data:
            for uri in ticket_data["artifact_uris"]:
                try:
                    artifact_contents = await ctx.read_resource(uri)
                    if artifact_contents and len(artifact_contents) > 0:
                        # Try each content item for valid JSON
                        for content_item in artifact_contents:
                            try:
                                artifact_data = json.loads(content_item.content)
                                artifacts.append(artifact_data)
                                break
                            except json.JSONDecodeError:
                                continue
                except Exception as artifact_error:
                    await ctx.warning(f"Error reading artifact {uri}: {str(artifact_error)}")
        
        ticket_data["artifacts"] = artifacts

        return json.dumps(ticket_data, indent=2)

    except Exception as e:
        await ctx.error(f"Failed to get ticket {id}: {str(e)}")
        raise
