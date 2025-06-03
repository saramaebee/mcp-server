"""
Copyright (c) 2025 DevRev, Inc.
SPDX-License-Identifier: MIT

This module implements the FastMCP server for DevRev integration.
"""

import json
from typing import Dict, Any

from fastmcp import FastMCP, Context
from mcp import types

# Import modular resources and tools
from .resources.ticket import ticket as ticket_resource
from .resources.timeline import timeline as timeline_resource
from .resources.timeline_entry import timeline_entry as timeline_entry_resource
from .resources.artifact import artifact as artifact_resource
from .resources.ticket_artifacts import ticket_artifacts as ticket_artifacts_resource
from .resources.work import works as work_resource
from .resources.issue import issue as issue_resource
from .tools.get_timeline_entries import get_timeline_entries as get_timeline_entries_tool
from .tools.get_ticket import get_ticket as get_ticket_tool
from .tools.search import search as search_tool
from .tools.create_object import create_object as create_object_tool
from .tools.update_object import update_object as update_object_tool
from .tools.download_artifact import download_artifact as download_artifact_tool
from .tools.get_work import get_work as get_work_tool
from .tools.get_issue import get_issue as get_issue_tool
from .tools.create_timeline_comment import create_timeline_comment as create_timeline_comment_tool

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
    description="""Search DevRev objects using hybrid search across multiple content types.

This tool performs intelligent search across DevRev data using natural language queries.
It combines semantic understanding with exact matching to find relevant content.

Supported namespaces:
- article: Search knowledge base articles and documentation
- issue: Search internal issues and bug reports  
- ticket: Search customer support tickets
- part: Search product parts and components
- dev_user: Search team members and user profiles

Usage examples:
- Find tickets about a specific technology: query="python dependency issues", namespace="ticket"
- Search for team expertise: query="frontend react developer", namespace="dev_user"
- Look up documentation: query="API authentication guide", namespace="article"
- Find related issues: query="memory leak in scanner", namespace="issue"

Returns enriched results with metadata, ownership, status, and organizational context
for efficient triage and analysis.""",
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
    description="Update existing DevRev tickets or issues with new information, descriptions, or titles. Accepts flexible ID formats for tickets/issues. Maintains object history and audit trails while allowing incremental updates as investigations progress.",
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
        id: The DevRev object ID - for tickets accepts TKT-12345, 12345, or full don:core format; 
            for issues accepts ISS-12345, 12345, or full don:core format
        type: The type of object ("issue" or "ticket")
        title: New title for the object (optional)
        body: New body/description for the object (optional)
    
    Returns:
        JSON string containing the updated object information
    """
    return await update_object_tool(id, type, title, body, ctx, devrev_cache)


# Specialized resource handlers for different DevRev object types

# Resource metadata constants
TICKET_RESOURCE_DESCRIPTION = "Access comprehensive DevRev ticket information with enriched timeline and artifacts. Supports multiple URI formats: numeric (12345), TKT format (TKT-12345), and full don:core IDs."
TICKET_RESOURCE_TAGS = ["ticket", "devrev", "customer-support", "enriched", "navigation"]

TIMELINE_RESOURCE_DESCRIPTION = "Access enriched ticket timeline with conversation flow, artifacts, and detailed visibility information. Includes customer context, visual visibility indicators (🔒🏢👥🌐), and comprehensive audit trail."
TIMELINE_RESOURCE_TAGS = ["timeline", "devrev", "customer-support", "enriched", "conversation", "visibility", "audit"]

TIMELINE_ENTRY_RESOURCE_DESCRIPTION = "Access individual timeline entry with detailed conversation data and navigation links. Provides specific entry context within ticket timeline."
TIMELINE_ENTRY_RESOURCE_TAGS = ["timeline-entry", "devrev", "customer-support", "conversation", "navigation"]

TICKET_ARTIFACTS_RESOURCE_DESCRIPTION = "Access all artifacts associated with a specific ticket. Returns collection of files, screenshots, and documents with download links and metadata."
TICKET_ARTIFACTS_RESOURCE_TAGS = ["artifacts", "devrev", "customer-support", "collection", "files", "navigation"]

ARTIFACT_RESOURCE_DESCRIPTION = "Access DevRev artifact metadata with temporary download URLs. Provides file information, content type, and secure download links."
ARTIFACT_RESOURCE_TAGS = ["artifact", "devrev", "files", "metadata", "download"]

WORK_RESOURCE_DESCRIPTION = "Access any DevRev work item with unified interface for tickets, issues, and other work types. Supports display ID formats (TKT-12345, ISS-9031) with navigation links."
WORK_RESOURCE_TAGS = ["work", "devrev", "unified", "tickets", "issues", "navigation"]

ISSUE_RESOURCE_DESCRIPTION = "Access comprehensive DevRev issue information with enriched timeline and artifacts. Supports multiple URI formats: numeric (9031), ISS format (ISS-9031), and full don:core IDs."
ISSUE_RESOURCE_TAGS = ["issue", "devrev", "internal-work", "enriched", "navigation"]

# Additional resource patterns for increased exposure
TIMELINE_ALT_RESOURCE_DESCRIPTION = "Access ticket timeline with alternative URI formats. Supports TKT- format and numeric IDs for flexible timeline access."
TIMELINE_ALT_RESOURCE_TAGS = ["timeline", "devrev", "customer-support", "enriched", "alternative-access"]

@mcp.resource(
    uri="devrev://tickets/{ticket_id}",
    description=TICKET_RESOURCE_DESCRIPTION,
    tags=TICKET_RESOURCE_TAGS
)
@mcp.resource(
    uri="devrev://tickets/TKT-{ticket_number}",
    description=TICKET_RESOURCE_DESCRIPTION,
    tags=TICKET_RESOURCE_TAGS
)
@mcp.resource(
    uri="devrev://tickets/don:core:dvrv-us-1:devo/{dev_org_id}:ticket/{ticket_number}",
    description=TICKET_RESOURCE_DESCRIPTION,
    tags=TICKET_RESOURCE_TAGS
)
async def ticket(ticket_id: str = None, ticket_number: str = None, dev_org_id: str = None, ctx: Context = None) -> str:
    """
    Access DevRev ticket details with navigation links.
    Supports multiple URI formats - all normalize to numeric ticket ID.
    
    Args:
        ticket_id: The DevRev ticket ID (numeric, e.g., 12345)
        ticket_number: The numeric part of the ticket ID (e.g., 12345 for TKT-12345)
        dev_org_id: The dev org ID (e.g., 118WAPdKBc) - unused but required for don:core format
        ctx: FastMCP context
    
    Returns:
        JSON string containing the ticket data with navigation links
    """
    # Normalize to ticket number - all formats end up as the numeric ID
    numeric_id = ticket_id or ticket_number
    return await ticket_resource(numeric_id, ctx, devrev_cache)

@mcp.resource(
    uri="devrev://tickets/{ticket_id}/timeline",
    description=TIMELINE_RESOURCE_DESCRIPTION,
    tags=TIMELINE_RESOURCE_TAGS
)
@mcp.resource(
    uri="devrev://timeline/{ticket_id}",
    description=TIMELINE_ALT_RESOURCE_DESCRIPTION,
    tags=TIMELINE_ALT_RESOURCE_TAGS
)
@mcp.resource(
    uri="devrev://timeline/TKT-{ticket_number}",
    description=TIMELINE_ALT_RESOURCE_DESCRIPTION,
    tags=TIMELINE_ALT_RESOURCE_TAGS
)
async def ticket_timeline(ticket_id: str = None, ticket_number: str = None, ctx: Context = None) -> str:
    """
    Access enriched timeline for a ticket with structured conversation format.
    Supports multiple URI formats for flexible access.
    
    Args:
        ticket_id: The DevRev ticket ID (numeric, e.g., 12345)
        ticket_number: The numeric part of the ticket ID (e.g., 12345 for TKT-12345)
        ctx: FastMCP context
    
    Returns:
        JSON string containing enriched timeline with customer context and conversation flow
    """
    # Normalize to ticket number
    numeric_id = ticket_id or ticket_number
    return await timeline_resource(numeric_id, ctx, devrev_cache)

@mcp.resource(
    uri="devrev://tickets/{ticket_id}/timeline/{entry_id}",
    description=TIMELINE_ENTRY_RESOURCE_DESCRIPTION,
    tags=TIMELINE_ENTRY_RESOURCE_TAGS
)
@mcp.resource(
    uri="devrev://tickets/TKT-{ticket_number}/timeline/{entry_id}",
    description=TIMELINE_ENTRY_RESOURCE_DESCRIPTION,
    tags=TIMELINE_ENTRY_RESOURCE_TAGS
)
@mcp.resource(
    uri="devrev://tickets/don:core:dvrv-us-1:devo/{dev_org_id}:ticket/{ticket_number}/timeline/{entry_id}",
    description=TIMELINE_ENTRY_RESOURCE_DESCRIPTION,
    tags=TIMELINE_ENTRY_RESOURCE_TAGS
)
async def timeline_entry(ticket_id: str = None, ticket_number: str = None, dev_org_id: str = None, entry_id: str = None, ctx: Context = None) -> str:
    """
    Access specific timeline entry details.
    Supports multiple URI formats for flexible access.
    
    Args:
        ticket_id: The DevRev ticket ID (numeric, e.g., 12345)
        ticket_number: The numeric part of the ticket ID (e.g., 12345 for TKT-12345)
        dev_org_id: The dev org ID (e.g., 118WAPdKBc) - unused but required for don:core format
        entry_id: The timeline entry ID
        ctx: FastMCP context
    
    Returns:
        JSON string containing the timeline entry data with links
    """
    # Normalize to ticket number
    numeric_id = ticket_id or ticket_number
    
    # Construct full timeline ID if needed
    if not entry_id.startswith("don:core:"):
        # This is a simplified ID, we'll need to fetch it via the ticket timeline
        return await timeline_resource(numeric_id, ctx, devrev_cache)
    
    result = await timeline_entry_resource(entry_id, ctx, devrev_cache)
    
    # Add navigation links
    import json
    entry_data = json.loads(result)
    entry_data["links"] = {
        "ticket": f"devrev://tickets/{numeric_id}",
        "timeline": f"devrev://tickets/{numeric_id}/timeline"
    }
    
    return json.dumps(entry_data, indent=2)

@mcp.resource(
    uri="devrev://tickets/{ticket_id}/artifacts",
    description=TICKET_ARTIFACTS_RESOURCE_DESCRIPTION,
    tags=TICKET_ARTIFACTS_RESOURCE_TAGS
)
@mcp.resource(
    uri="devrev://tickets/TKT-{ticket_number}/artifacts",
    description=TICKET_ARTIFACTS_RESOURCE_DESCRIPTION,
    tags=TICKET_ARTIFACTS_RESOURCE_TAGS
)
@mcp.resource(
    uri="devrev://tickets/don:core:dvrv-us-1:devo/{dev_org_id}:ticket/{ticket_number}/artifacts",
    description=TICKET_ARTIFACTS_RESOURCE_DESCRIPTION,
    tags=TICKET_ARTIFACTS_RESOURCE_TAGS
)
async def ticket_artifacts(ticket_id: str = None, ticket_number: str = None, dev_org_id: str = None, ctx: Context = None) -> str:
    """
    Access all artifacts for a ticket.
    Supports multiple URI formats for flexible access.
    
    Args:
        ticket_id: The DevRev ticket ID (numeric, e.g., 12345)
        ticket_number: The numeric part of the ticket ID (e.g., 12345 for TKT-12345)
        dev_org_id: The dev org ID (e.g., 118WAPdKBc) - unused but required for don:core format
        ctx: FastMCP context
    
    Returns:
        JSON string containing artifacts with navigation links
    """
    # Normalize to ticket number
    numeric_id = ticket_id or ticket_number
    return await ticket_artifacts_resource(numeric_id, ctx, devrev_cache)

@mcp.resource(
    uri="devrev://artifacts/{artifact_id}",
    description=ARTIFACT_RESOURCE_DESCRIPTION,
    tags=ARTIFACT_RESOURCE_TAGS
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

@mcp.resource(
    uri="devrev://works/don:core:dvrv-us-1:devo/{dev_org_id}:{work_type}/{work_number}",
    description=WORK_RESOURCE_DESCRIPTION,
    tags=WORK_RESOURCE_TAGS
)
@mcp.resource(
    uri="devrev://works/{work_id}",
    description=WORK_RESOURCE_DESCRIPTION,
    tags=WORK_RESOURCE_TAGS
)
async def works(ctx: Context, work_id: str | None = None, work_type: str | None = None, work_number: str | None = None, dev_org_id: str | None = None) -> str:
    """
    Access DevRev work item details using unified work ID format.
    
    Args:
        work_id: The DevRev work ID (e.g., TKT-12345, ISS-9031)
    
    Returns:
        JSON string containing the work item data with navigation links
    """
    if work_id is not None:
        return await work_resource(work_id, ctx, devrev_cache)
    elif work_type is not None and work_number is not None:
        work_id = f"{work_type}-{work_number}"
        return await work_resource(work_id, ctx, devrev_cache)
    else:
        raise ValueError("work_type and work_number are required if work_id is not provided")


@mcp.resource(
    uri="devrev://issues/{issue_number}",
    description=ISSUE_RESOURCE_DESCRIPTION,
    tags=ISSUE_RESOURCE_TAGS
)
@mcp.resource(
    uri="devrev://issues/ISS-{issue_number}",
    description=ISSUE_RESOURCE_DESCRIPTION,
    tags=ISSUE_RESOURCE_TAGS
)
@mcp.resource(
    uri="devrev://issues/don:core:dvrv-us-1:devo/{dev_org_id}:issue/{issue_number}",
    description=ISSUE_RESOURCE_DESCRIPTION,
    tags=ISSUE_RESOURCE_TAGS
)
async def issue(issue_number: str = None, dev_org_id: str = None, ctx: Context = None) -> str:
    """
    Access DevRev issue details with navigation links.
    Supports multiple URI formats - all normalize to numeric issue number.
    
    Args:
        issue_id: The DevRev issue ID (numeric, e.g., 9031)
        issue_number: The numeric part of the issue ID (e.g., 9031 for ISS-9031)
        dev_org_id: The dev org ID (e.g., 118WAPdKBc) - unused but required for don:core format
        ctx: FastMCP context
    
    Returns:
        JSON string containing the issue data with navigation links
    """
    # Normalize to issue number - all formats end up as the numeric ID
    return await issue_resource(issue_number, ctx, devrev_cache)


@mcp.resource(
    uri="devrev://issues/{issue_id}/timeline",
    description="Access enriched issue timeline with conversation flow, artifacts, and detailed visibility information. Includes internal context, visual visibility indicators (🔒🏢👥🌐), and comprehensive audit trail.",
    tags=["issue-timeline", "devrev", "internal-work", "enriched", "conversation", "visibility", "audit"]
)
@mcp.resource(
    uri="devrev://issues/ISS-{issue_number}/timeline",
    description="Access enriched issue timeline with conversation flow, artifacts, and detailed visibility information. Includes internal context, visual visibility indicators (🔒🏢👥🌐), and comprehensive audit trail.",
    tags=["issue-timeline", "devrev", "internal-work", "enriched", "conversation", "visibility", "audit"]
)
async def issue_timeline(issue_id: str = None, issue_number: str = None, ctx: Context = None) -> str:
    """
    Access enriched timeline for an issue with structured conversation format.
    Supports multiple URI formats for flexible access.
    
    Args:
        issue_id: The DevRev issue ID (numeric, e.g., 9031)
        issue_number: The numeric part of the issue ID (e.g., 9031 for ISS-9031)
        ctx: FastMCP context
    
    Returns:
        JSON string containing enriched timeline with internal context and conversation flow
    """
    # Normalize to issue number
    numeric_id = issue_id or issue_number
    
    # Get issue data to extract timeline
    issue_data_str = await issue_resource(numeric_id, ctx, devrev_cache)
    issue_data = json.loads(issue_data_str)
    timeline_entries = issue_data.get("timeline_entries", [])
    
    # Build simplified timeline structure for issues
    result = {
        "issue_id": f"ISS-{numeric_id}",
        "timeline_entries": timeline_entries,
        "total_entries": len(timeline_entries),
        "links": {
            "issue": f"devrev://issues/{numeric_id}",
            "artifacts": f"devrev://issues/{numeric_id}/artifacts"
        }
    }
    
    return json.dumps(result, indent=2)


@mcp.resource(
    uri="devrev://issues/{issue_id}/artifacts",
    description="Access all artifacts associated with a specific issue. Returns collection of files, screenshots, and documents with download links and metadata.",
    tags=["issue-artifacts", "devrev", "internal-work", "collection", "files", "navigation"]
)
@mcp.resource(
    uri="devrev://issues/ISS-{issue_number}/artifacts",
    description="Access all artifacts associated with a specific issue. Returns collection of files, screenshots, and documents with download links and metadata.",
    tags=["issue-artifacts", "devrev", "internal-work", "collection", "files", "navigation"]
)
async def issue_artifacts(issue_id: str = None, issue_number: str = None, ctx: Context = None) -> str:
    """
    Access all artifacts for an issue.
    Supports multiple URI formats for flexible access.
    
    Args:
        issue_id: The DevRev issue ID (numeric, e.g., 9031)
        issue_number: The numeric part of the issue ID (e.g., 9031 for ISS-9031)
        ctx: FastMCP context
    
    Returns:
        JSON string containing artifacts with navigation links
    """
    # Normalize to issue number
    numeric_id = issue_id or issue_number
    
    # Get issue data to extract artifacts
    issue_data_str = await issue_resource(numeric_id, ctx, devrev_cache)
    issue_data = json.loads(issue_data_str)
    artifacts = issue_data.get("artifacts", [])
    
    # Add navigation links to each artifact
    for artifact in artifacts:
        artifact_id = artifact.get("id", "").split("/")[-1] if artifact.get("id") else ""
        if artifact_id:
            artifact["links"] = {
                "self": f"devrev://artifacts/{artifact_id}",
                "issue": f"devrev://issues/{numeric_id}"
            }
    
    result = {
        "artifacts": artifacts,
        "total_artifacts": len(artifacts),
        "links": {
            "issue": f"devrev://issues/{numeric_id}",
            "timeline": f"devrev://issues/{numeric_id}/timeline"
        }
    }
    
    return json.dumps(result, indent=2)


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

@mcp.tool(
    name="get_work",
    description="Get any DevRev work item (ticket, issue, etc.) by ID. Supports unified access to all work item types using their display IDs like TKT-12345, ISS-9031, etc.",
    tags=["work", "devrev", "tickets", "issues", "unified", "get"]
)
async def get_work(id: str, ctx: Context) -> str:
    """
    Get a DevRev work item by ID.
    
    Args:
        id: The DevRev work ID - accepts TKT-12345, ISS-9031, or any work item format
    
    Returns:
        JSON string containing the work item data
    """
    return await get_work_tool(id, ctx)

@mcp.tool(
    name="get_issue",
    description="Get a DevRev issue by ID. Supports unified access to issue using display IDs like ISS-9031, numeric IDs, or full don:core format.",
    tags=["issue", "devrev", "internal-work", "get"]
)
async def get_issue(id: str, ctx: Context) -> str:
    """
    Get a DevRev issue by ID.
    
    Args:
        id: The DevRev issue ID - accepts ISS-9031, 9031, or full don:core format
    
    Returns:
        JSON string containing the issue data
    """
    return await get_issue_tool(id, ctx)

@mcp.tool(
    name="create_timeline_comment",
    description="""Create an internal timeline comment on a DevRev ticket.
    
Adds a comment to the ticket's timeline that is only visible to internal team members 
for documentation and collaboration purposes.

⚠️ REQUIRES MANUAL REVIEW - This tool modifies ticket data and should always be 
manually approved before execution.""",
    tags=["timeline", "comment", "devrev", "internal", "create", "dangerous"]
)
async def create_timeline_comment(work_id: str, body: str, ctx: Context) -> str:
    """
    Create an internal timeline comment on a DevRev ticket.
    
    Args:
        work_id: The DevRev work ID (e.g., "12345", "TKT-12345", "ISS-12345)
        body: The comment text to add to the timeline
    
    Returns:
        JSON string containing the created timeline entry data
    """
    return await create_timeline_comment_tool(work_id, body, ctx)

def main():
    """Main entry point for the DevRev MCP server."""
    # Run the server
    mcp.run()

if __name__ == "__main__":
    main()