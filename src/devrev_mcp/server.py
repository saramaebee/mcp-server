"""
Copyright (c) 2025 DevRev, Inc.
SPDX-License-Identifier: MIT

This module implements the FastMCP server for DevRev integration.
"""

from typing import Dict, Any

from fastmcp import FastMCP, Context
from mcp import types

# Import modular resources and tools
from .resources.ticket import ticket as ticket_resource
from .resources.timeline_entry import timeline_entry as timeline_entry_resource
from .resources.artifact import artifact as artifact_resource
from .tools.get_object import get_object as get_object_tool
from .tools.get_timeline_entries import get_timeline_entries as get_timeline_entries_tool
from .tools.get_ticket import get_ticket as get_ticket_tool
from .tools.search import search as search_tool
from .tools.create_object import create_object as create_object_tool
from .tools.update_object import update_object as update_object_tool
from .tools.download_artifact import download_artifact as download_artifact_tool


# Create the FastMCP server
mcp = FastMCP(
    name="devrev_mcp",
    version="0.1.1",
    description="DevRev MCP Server - Provides tools for interacting with DevRev API"
)

# Store DevRev resources (works, comments, etc.) for resource access
devrev_cache = {}

@mcp.tool(
    name="search",
    description="Search DevRev objects using hybrid search. Supports natural language queries across tickets, issues, articles, parts, and users. Returns enriched results with metadata, ownership, status, and organizational context for efficient triage and analysis.",
    tags=["search", "devrev", "tickets", "issues", "articles", "hybrid-search"]
)
async def search(query: str, namespace: str, ctx: Context) -> str:
    """
    Search DevRev using the provided query and return parsed, useful information.
    
    Args:
        query: The search query string
        namespace: The namespace to search in (article, issue, ticket, part, dev_user)
    
    Returns:
        JSON string containing parsed search results with key information
    """
    return await search_tool(query, namespace, ctx)

@mcp.tool(
    name="create_object",
    description="Create new DevRev tickets or issues with full metadata support. Supports both customer-facing tickets and internal issues with proper assignment, categorization, and detailed descriptions for workflow automation.",
    tags=["create", "devrev", "tickets", "issues", "workflow", "automation"]
)
async def create_object(
    type: str,
    title: str, 
    applies_to_part: str,
    body: str = "",
    owned_by: list[str] = None,
    ctx: Context = None
) -> str:
    """
    Create a new issue or ticket in DevRev.
    
    Args:
        type: The type of object to create ("issue" or "ticket")
        title: The title/summary of the object
        applies_to_part: The part ID this object applies to
        body: The body/description of the object (optional)
        owned_by: List of user IDs who should own this object (optional)
    
    Returns:
        JSON string containing the created object information
    """
    return await create_object_tool(type, title, applies_to_part, body, owned_by, ctx)

@mcp.tool(
    name="update_object", 
    description="Update existing DevRev tickets or issues with new information, descriptions, or titles. Maintains object history and audit trails while allowing incremental updates as investigations progress.",
    tags=["update", "devrev", "tickets", "issues", "maintenance", "audit"]
)
async def update_object(
    id: str,
    type: str,
    title: str = None,
    body: str = None,
    ctx: Context = None
) -> str:
    """
    Update an existing issue or ticket in DevRev.
    
    Args:
        id: The ID of the object to update
        type: The type of object ("issue" or "ticket")
        title: New title for the object (optional)
        body: New body/description for the object (optional)
    
    Returns:
        JSON string containing the updated object information
    """
    return await update_object_tool(id, type, title, body, ctx, devrev_cache)

@mcp.tool(
    name="get_object",
    description="Retrieve comprehensive information about any DevRev object including tickets, issues, parts, and users. Returns complete metadata, relationships, assignment details, and history for thorough analysis and investigation.",
    tags=["retrieve", "devrev", "objects", "metadata", "investigation", "analysis"]
)
async def get_object(id: str, ctx: Context) -> str:
    """
    Get all information about a DevRev issue and ticket using its ID.
    
    Args:
        id: The DevRev object ID
    
    Returns:
        JSON string containing the object information
    """
    return await get_object_tool(id, ctx, devrev_cache)

# Specialized resource handlers for different DevRev object types

@mcp.resource(
    uri="devrev://tickets/{ticket_id}",
    description="Access comprehensive DevRev ticket information with navigation links to related resources. Includes customer details, status progression, assignment history, and navigation to timeline and artifacts.",
    tags=["ticket", "devrev", "customer-support", "navigation"]
)
async def ticket(ticket_id: str, ctx: Context) -> str:
    """
    Access DevRev ticket details with navigation links.
    
    Args:
        ticket_id: The DevRev ticket ID (e.g., 12345 for TKT-12345)
    
    Returns:
        JSON string containing the ticket data with navigation links
    """
    result = await ticket_resource(ticket_id, ctx, devrev_cache)
    
    # Debug: Log the result details
    await ctx.info(f"ticket_resource returned result type: {type(result)}, length: {len(result) if result else 0}")
    if result:
        await ctx.info(f"Result preview: {repr(result[:100])}")
    
    # Debug: Check if result is empty
    if not result:
        await ctx.error(f"ticket_resource returned empty result for ticket_id: {ticket_id}")
        raise ValueError(f"Empty result from ticket_resource for ticket {ticket_id}")
    
    # Parse the result and add navigation links
    import json
    ticket_data = json.loads(result)
    ticket_data["links"] = {
        "timeline": f"devrev://tickets/{ticket_id}/timeline",
        "artifacts": f"devrev://tickets/{ticket_id}/artifacts"
    }
    
    # Return JSON string as expected by MCP framework
    return json.dumps(ticket_data, indent=2)

@mcp.resource(
    uri="devrev://tickets/{ticket_id}/timeline",
    description="Access enriched timeline for a ticket with customer context, conversation flow, and artifacts. Returns token-efficient structured format focusing on support workflow.",
    tags=["timeline", "enriched", "devrev", "conversation", "artifacts"]
)
async def ticket_timeline(ticket_id: str, ctx: Context) -> str:
    """
    Access enriched timeline for a ticket with structured conversation format.
    
    Args:
        ticket_id: The DevRev ticket ID (e.g., 12345 for TKT-12345)
    
    Returns:
        JSON string containing enriched timeline with customer context and conversation flow
    """
    from .utils import make_devrev_request
    import json
    
    try:
        # Normalize ticket ID to handle various formats - extract just the number then format properly
        if ticket_id.upper().startswith("TKT-"):
            # Extract numeric part and reformat
            numeric_id = ticket_id[4:]  # Remove TKT- or tkt-
            normalized_id = f"TKT-{numeric_id}"
        else:
            normalized_id = f"TKT-{ticket_id}"
        
        # Get ticket details for customer and workspace info
        ticket_response = make_devrev_request("works.get", {"id": normalized_id})
        if ticket_response.status_code != 200:
            raise ValueError(f"Failed to fetch ticket {normalized_id}")
        
        ticket_data = ticket_response.json()
        work = ticket_data.get("work", {})
        
        # Get timeline entries with pagination
        all_entries = []
        cursor = None
        page_count = 0
        max_pages = 50  # Safety limit to prevent infinite loops
        
        while page_count < max_pages:
            request_payload = {
                "object": normalized_id,
                "limit": 50  # Use DevRev's default limit
            }
            if cursor:
                request_payload["cursor"] = cursor
                request_payload["mode"] = "after"  # Get entries after this cursor
            
            timeline_response = make_devrev_request(
                "timeline-entries.list",
                request_payload
            )
            
            if timeline_response.status_code != 200:
                raise ValueError(f"Failed to fetch timeline for {normalized_id}")
            
            timeline_data = timeline_response.json()
            page_entries = timeline_data.get("timeline_entries", [])
            all_entries.extend(page_entries)
            
            # Check for next page using DevRev's cursor system
            cursor = timeline_data.get("next_cursor")
            page_count += 1
            
            await ctx.info(f"DEBUG: Fetched page {page_count} with {len(page_entries)} entries, total so far: {len(all_entries)}")
            
            # Break if no more pages or no entries in this page
            if not cursor or len(page_entries) == 0:
                break
        
        await ctx.info(f"DEBUG: Found {len(all_entries)} timeline entries for {normalized_id}")
        
        # Extract customer information
        customer_info = {}
        created_by = work.get("created_by", {})
        if created_by:
            customer_info = {
                "name": created_by.get("display_name", "Unknown"),
                "email": created_by.get("email", ""),
                "type": "customer" if created_by.get("type") == "user" else "system"
            }
        
        # Build enriched schema
        result = {
            "summary": {
                "ticket_id": normalized_id,
                "customer": customer_info.get("email", customer_info.get("name", "Unknown")),
                "workspace": work.get("owned_by", [{}])[0].get("display_name", "Unknown Workspace") if work.get("owned_by") else "Unknown Workspace",
                "subject": work.get("title", "No title"),
                "current_stage": work.get("stage", {}).get("name", "unknown"),
                "created_date": work.get("created_date"),
                "total_artifacts": 0
            },
            "conversation_thread": [],
            "key_events": [],
            "all_artifacts": []
        }
        
        # Process timeline entries into conversation and events
        conversation_seq = 1
        artifacts_found = {}  # artifact_id -> artifact_info dict
        
        for entry in all_entries:
            entry_type = entry.get("type", "")
            timestamp = entry.get("created_date", "")
            
            # Handle conversation entries (comments)
            if entry_type == "timeline_comment":
                body = entry.get("body", "")
                author = entry.get("created_by", {})
                
                # Determine speaker type
                speaker_type = "support"
                if author.get("email") == customer_info.get("email"):
                    speaker_type = "customer"
                elif "system" in author.get("display_name", "").lower():
                    speaker_type = "system"
                
                conversation_entry = {
                    "seq": conversation_seq,
                    "timestamp": timestamp,
                    "event_type": entry_type,
                    "speaker": {
                        "name": author.get("display_name", author.get("email", "Unknown")),
                        "type": speaker_type
                    },
                    "message": body,
                    "artifacts": []
                }
                
                # Add artifacts if present
                if entry.get("artifacts"):
                    for artifact in entry["artifacts"]:
                        artifact_id = artifact.get("id")
                        artifact_info = {
                            "id": artifact_id,
                            "display_id": artifact.get("display_id"),
                            "type": artifact.get("file", {}).get("type", "unknown"),
                            "attached_to_message": conversation_seq,
                            "resource_uri": f"devrev://artifacts/{artifact_id}"
                        }
                        conversation_entry["artifacts"].append(artifact_info)
                        artifacts_found[artifact_id] = artifact_info
                
                # Add timeline entry navigation link
                entry_id = entry.get("id", "").split("/")[-1] if entry.get("id") else ""
                if entry_id:
                    conversation_entry["timeline_entry_uri"] = f"devrev://tickets/{ticket_id}/timeline/{entry_id}"
                
                result["conversation_thread"].append(conversation_entry)
                conversation_seq += 1
                
                # Update last message timestamps
                if speaker_type == "customer":
                    result["summary"]["last_customer_message"] = timestamp
                elif speaker_type == "support":
                    result["summary"]["last_support_response"] = timestamp
            
            # Handle key events
            elif entry_type in ["work_created", "stage_updated", "part_suggested", "work_updated"]:
                event_info = {
                    "type": entry_type.replace("work_", "").replace("_", " "),
                    "event_type": entry_type,
                    "timestamp": timestamp
                }
                
                # Add context for stage updates
                if entry_type == "stage_updated" and entry.get("stage_updated"):
                    stage_info = entry["stage_updated"]
                    event_info["from_stage"] = stage_info.get("old_stage", {}).get("name")
                    event_info["to_stage"] = stage_info.get("new_stage", {}).get("name")
                
                # Add author information if available
                author = entry.get("created_by", {})
                if author:
                    event_info["actor"] = {
                        "name": author.get("display_name", author.get("email", "System")),
                        "type": "customer" if author.get("email") == customer_info.get("email") else "support"
                    }
                
                result["key_events"].append(event_info)
            
            # Handle all other event types to preserve information
            else:
                # Skip entries without meaningful content
                if not entry_type or entry_type in ["", "unknown"]:
                    continue
                
                # Determine if this is likely a conversation-like entry
                body = entry.get("body", "").strip()
                author = entry.get("created_by", {})
                
                if body:  # Has content, treat as conversation
                    speaker_type = "support"
                    if author.get("email") == customer_info.get("email"):
                        speaker_type = "customer"
                    elif "system" in author.get("display_name", "").lower():
                        speaker_type = "system"
                    
                    conversation_entry = {
                        "seq": conversation_seq,
                        "timestamp": timestamp,
                        "event_type": entry_type,
                        "speaker": {
                            "name": author.get("display_name", author.get("email", "Unknown")),
                            "type": speaker_type
                        },
                        "message": body,
                        "artifacts": []
                    }
                    
                    # Add timeline entry navigation link
                    entry_id = entry.get("id", "").split("/")[-1] if entry.get("id") else ""
                    if entry_id:
                        conversation_entry["timeline_entry_uri"] = f"devrev://tickets/{ticket_id}/timeline/{entry_id}"
                    
                    result["conversation_thread"].append(conversation_entry)
                    conversation_seq += 1
                    
                    # Update last message timestamps
                    if speaker_type == "customer":
                        result["summary"]["last_customer_message"] = timestamp
                    elif speaker_type == "support":
                        result["summary"]["last_support_response"] = timestamp
                        
                else:  # No content, treat as event
                    event_info = {
                        "type": entry_type.replace("_", " "),
                        "event_type": entry_type,
                        "timestamp": timestamp
                    }
                    
                    # Add author information if available
                    if author:
                        event_info["actor"] = {
                            "name": author.get("display_name", author.get("email", "System")),
                            "type": "customer" if author.get("email") == customer_info.get("email") else "support"
                        }
                    
                    result["key_events"].append(event_info)
        
        # Set artifact count and list
        result["all_artifacts"] = list(artifacts_found.values())
        result["summary"]["total_artifacts"] = len(artifacts_found)
        
        # Add navigation links
        result["links"] = {
            "ticket": f"devrev://tickets/{ticket_id}"
        }
        
        if result["all_artifacts"]:
            result["links"]["artifacts"] = f"devrev://tickets/{ticket_id}/artifacts"
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        await ctx.error(f"Failed to get timeline for ticket {ticket_id}: {str(e)}")
        raise ValueError(f"Timeline for ticket {ticket_id} not found: {str(e)}")

@mcp.resource(
    uri="devrev://tickets/{ticket_id}/timeline/{entry_id}",
    description="Access individual timeline entry with detailed conversation data and navigation links.",
    tags=["timeline", "entry", "devrev", "conversation"]
)
async def timeline_entry(ticket_id: str, entry_id: str, ctx: Context) -> str:
    """
    Access specific timeline entry details.
    
    Args:
        ticket_id: The DevRev ticket ID
        entry_id: The timeline entry ID
    
    Returns:
        JSON string containing the timeline entry data with links
    """
    # Construct full timeline ID if needed
    if not entry_id.startswith("don:core:"):
        # This is a simplified ID, we'll need to fetch it via the ticket timeline
        return await ticket_timeline(ticket_id, ctx)
    
    result = await timeline_entry_resource(entry_id, ctx, devrev_cache)
    
    # Add navigation links
    import json
    entry_data = json.loads(result)
    entry_data["links"] = {
        "ticket": f"devrev://tickets/{ticket_id}",
        "timeline": f"devrev://tickets/{ticket_id}/timeline"
    }
    
    return json.dumps(entry_data, indent=2)

@mcp.resource(
    uri="devrev://tickets/{ticket_id}/artifacts",
    description="Access all artifacts associated with a specific ticket. Returns list of files, screenshots, and documents attached to the ticket.",
    tags=["artifacts", "collection", "devrev", "ticket-artifacts"]
)
async def ticket_artifacts(ticket_id: str, ctx: Context) -> str:
    """
    Access all artifacts for a ticket.
    
    Args:
        ticket_id: The DevRev ticket ID (e.g., 12345 for TKT-12345)
    
    Returns:
        JSON string containing artifacts with navigation links
    """
    # Get ticket data to extract artifacts
    ticket_data_str = await ticket_resource(ticket_id, ctx, devrev_cache)
    
    import json
    ticket_data = json.loads(ticket_data_str)
    artifacts = ticket_data.get("artifacts", [])
    
    # Add navigation links to each artifact
    for artifact in artifacts:
        artifact_id = artifact.get("id", "").split("/")[-1] if artifact.get("id") else ""
        if artifact_id:
            artifact["links"] = {
                "self": f"devrev://artifacts/{artifact_id}",
                "ticket": f"devrev://tickets/{ticket_id}"
            }
    
    result = {
        "artifacts": artifacts,
        "links": {
            "ticket": f"devrev://tickets/{ticket_id}"
        }
    }
    
    return json.dumps(result, indent=2)

@mcp.resource(
    uri="devrev://artifacts/{artifact_id}",
    description="Access DevRev artifact metadata with temporary download URLs and reverse links to associated tickets.",
    tags=["artifact", "devrev", "files", "reverse-links"]
)
async def artifact(artifact_id: str, ctx: Context) -> str:
    """
    Access DevRev artifact metadata with reverse links.
    
    Args:
        artifact_id: The DevRev artifact ID
    
    Returns:
        JSON string containing the artifact metadata with reverse links
    """
    result = await artifact_resource(artifact_id, ctx, devrev_cache)
    
    # Add reverse links (would need to be implemented based on DevRev API capabilities)
    import json
    artifact_data = json.loads(result)
    artifact_data["links"] = {
        "tickets": f"devrev://artifacts/{artifact_id}/tickets"
    }
    
    return json.dumps(artifact_data, indent=2)

@mcp.resource(
    uri="devrev://artifacts/{artifact_id}/tickets",
    description="Access all tickets that reference this artifact. Provides reverse lookup from artifacts to tickets.",
    tags=["artifact", "reverse-links", "devrev", "tickets"]
)
async def artifact_tickets(artifact_id: str, ctx: Context) -> str:
    """
    Access tickets that reference this artifact.
    
    Args:
        artifact_id: The DevRev artifact ID
    
    Returns:
        JSON string containing linked tickets
    """
    # This would require a search or reverse lookup in DevRev API
    # For now, return a placeholder structure
    import json
    
    result = {
        "linked_tickets": [],  # Would be populated with actual ticket URIs
        "message": "Reverse artifact lookup not yet implemented",
        "links": {
            "artifact": f"devrev://artifacts/{artifact_id}"
        }
    }
    
    return json.dumps(result, indent=2)

# Add dynamic resource access for DevRev objects
@mcp.resource(
    uri="devrev://{id}",
    description="Universal DevRev object accessor supporting any object type including tickets, issues, comments, parts, and users. Automatically routes to specialized handlers based on object type for optimal data enrichment and presentation.",
    tags=["devrev", "universal", "router", "objects", "tickets", "issues", "comments"]
)
async def get_devrev_resource(id: str, ctx: Context) -> str:
    """
    Access any DevRev object (tickets, comments, issues, etc.) by its full DevRev ID.
    Routes to specialized handlers based on object type.
    
    Args:
        id: The DevRev object ID
    
    Returns:
        JSON string containing the object data
    """
    try:
        await ctx.info(f"Routing resource request for {id} to specialized handler")
        
        # Route to specialized handlers based on ID pattern
        if ":ticket/" in id:
            if ":comment/" in id:
                # This is a timeline entry (comment)
                return await timeline_entry(id, ctx)
            else:
                # This is a ticket
                return await ticket(id, ctx)
        elif ":artifact/" in id:
            # This is an artifact
            artifact_id = id.split(":artifact/")[1]
            return await artifact(artifact_id, ctx)
        else:
            # Fall back to generic object handler for other types
            await ctx.info(f"Using generic object handler for {id}")
            return await get_object(id, ctx)
        
    except Exception as e:
        await ctx.error(f"Failed to get resource {id}: {str(e)}")
        raise ValueError(f"Resource {id} not found: {str(e)}")

@mcp.tool(
    name="get_timeline_entries",
    description="Retrieve chronological timeline of all activity on a DevRev ticket including comments, status changes, assignments, and system events. Essential for understanding ticket progression, customer interactions, and audit trails. Accepts flexible ID formats (TKT-12345, 12345, or full don: format) and provides multiple output formats for different use cases.",
    tags=["timeline", "devrev", "tickets", "history", "conversations", "audit"]
)
async def get_timeline_entries(id: str, format: str = "summary", ctx: Context = None) -> str:
    """
    Get all timeline entries for a DevRev ticket using its ID with flexible formatting.
    
    Args:
        id: The DevRev ticket ID - accepts TKT-12345, 12345, or full don:core format
        format: Output format - "summary" (key info), "detailed" (conversation focus), or "full" (complete data)
    """
    return await get_timeline_entries_tool(id, ctx, format)

@mcp.tool(
    name="get_ticket",
    description="Get a DevRev ticket with all associated timeline entries and artifacts. Provides enriched ticket data with complete conversation history and attached files for comprehensive support analysis.",
    tags=["ticket", "devrev", "enriched", "timeline", "artifacts", "support"]
)
async def get_ticket(id: str, ctx: Context) -> str:
    """
    Get a DevRev ticket with all associated timeline entries and artifacts.
    
    Args:
        id: The DevRev ticket ID - accepts TKT-12345, 12345, or full don:core format
    
    Returns:
        JSON string containing the ticket data with timeline entries and artifacts
    """
    return await get_ticket_tool(id, ctx)

@mcp.tool(
    name="download_artifact",
    description="Download a DevRev artifact to a specified directory. Retrieves the artifact file and saves it locally with proper metadata.",
    tags=["download", "artifact", "devrev", "files", "local-storage"]
)
async def download_artifact(artifact_id: str, download_directory: str, ctx: Context) -> str:
    """
    Download a DevRev artifact to a specified directory.
    
    Args:
        artifact_id: The DevRev artifact ID to download
        download_directory: The local directory path where the artifact should be saved
    
    Returns:
        JSON string containing download result and file information
    """
    return await download_artifact_tool(artifact_id, download_directory, ctx)

def main():
    """Main entry point for the DevRev MCP server."""
    # Run the server
    mcp.run()

if __name__ == "__main__":
    main()