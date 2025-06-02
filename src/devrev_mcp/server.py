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
from .resources.timeline import timeline as timeline_resource
from .resources.timeline_entry import timeline_entry as timeline_entry_resource
from .resources.artifact import artifact as artifact_resource
from .resources.ticket_artifacts import ticket_artifacts as ticket_artifacts_resource
from .tools.get_timeline_entries import get_timeline_entries as get_timeline_entries_tool
from .tools.get_ticket import get_ticket as get_ticket_tool
from .tools.search import search as search_tool
from .tools.create_object import create_object as create_object_tool
from .tools.update_object import update_object as update_object_tool
from .tools.download_artifact import download_artifact as download_artifact_tool

# Import new types for visibility handling
from .types import VisibilityInfo, TimelineEntryType, format_visibility_summary

# Create the FastMCP server
mcp = FastMCP(
    name="devrev_mcp",
    version="0.1.1",
    description="DevRev MCP Server - Provides tools for interacting with DevRev API"
)

# Import cache utility to prevent unbounded memory growth
from .cache import devrev_cache

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
    return await ticket_resource(ticket_id, ctx, devrev_cache)

@mcp.resource(
    uri="devrev://tickets/{ticket_id}/timeline",
    description="""
    Access enriched timeline for a ticket with customer context, conversation flow, 
    artifacts, and detailed visibility information.
    
    Returns token-efficient structured format focusing on support workflow with 
    comprehensive visibility data:
    - Each entry includes visibility_info showing who can see it (private/internal/external/public)
    - Summary includes visibility breakdown and customer-visible percentage
    - Visual indicators (🔒🏢👥🌐) help identify visibility levels at a glance
    - Visibility levels: private (creator only), internal (dev org), external (dev org + customers), public (everyone)
    """,
    tags=["timeline", "enriched", "devrev", "conversation", "artifacts", "visibility"]
)
async def ticket_timeline(ticket_id: str, ctx: Context) -> str:
    """
    Access enriched timeline for a ticket with structured conversation format.
    
    Args:
        ticket_id: The DevRev ticket ID (e.g., 12345 for TKT-12345)
    
    Returns:
        JSON string containing enriched timeline with customer context and conversation flow
    """
    return await timeline_resource(ticket_id, ctx, devrev_cache)

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
        return await timeline_resource(ticket_id, ctx)
    
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
    return await ticket_artifacts_resource(ticket_id, ctx, devrev_cache)

@mcp.resource(
    uri="devrev://artifacts/{artifact_id}",
    description="Access DevRev artifact metadata with temporary download URLs.",
    tags=["artifact", "devrev", "files"]
)
async def artifact(artifact_id: str, ctx: Context) -> str:
    """
    Access DevRev artifact metadata.
    
    Args:
        artifact_id: The DevRev artifact ID
    
    Returns:
        JSON string containing the artifact metadata
    """
    result = await artifact_resource(artifact_id, ctx, devrev_cache)
    
    # Return the artifact data directly
    return result


@mcp.tool(
    name="get_timeline_entries",
    description="""
    Retrieve chronological timeline of all activity on a DevRev ticket including 
    comments, status changes, assignments, and system events with detailed visibility information.
    
    Essential for understanding ticket progression, customer interactions, and audit trails. 
    Each entry includes:
    - Visibility level (private/internal/external/public) showing who can access it
    - Visual indicators (🔒🏢👥🌐) for quick visibility identification  
    - Percentage breakdown of customer-visible vs internal-only content
    - Audience information (creator only, dev org, dev org + customers, everyone)
    
    Accepts flexible ID formats (TKT-12345, 12345, or full don: format) and provides 
    multiple output formats for different use cases.
    """,
    tags=["timeline", "devrev", "tickets", "history", "conversations", "audit", "visibility"]
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
    description="Download a DevRev artifact to a specified directory using its full artifact ID. Requires the complete don:core artifact ID format (e.g., don:core:dvrv-us-1:devo/123:artifact/456), not just the numeric ID. Retrieves the artifact file and saves it locally with proper metadata.",
    tags=["download", "artifact", "devrev", "files", "local-storage"]
)
async def download_artifact(artifact_id: str, download_directory: str, ctx: Context) -> str:
    """
    Download a DevRev artifact to a specified directory.
    
    Args:
        artifact_id: The full DevRev artifact ID in don:core format (e.g., don:core:dvrv-us-1:devo/123:artifact/456). 
                    The numeric ID alone (e.g., 456) will not work.
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