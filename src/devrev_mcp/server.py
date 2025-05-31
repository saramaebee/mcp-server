"""
Copyright (c) 2025 DevRev, Inc.
SPDX-License-Identifier: MIT

This module implements the FastMCP server for DevRev integration.
"""

import json
import os
from typing import Dict, Any

from fastmcp import FastMCP, Context
from mcp import types
from .utils import make_devrev_request

# Check debug mode and store state
DEBUG_ENABLED = os.environ.get("DRMCP_DEBUG") == "1"
DEBUG_MESSAGE = "🐛 DEBUG MODE ENABLED - sara wuz here" if DEBUG_ENABLED else "🐛 DEBUG MODE DISABLED - sara wuz here"

# Create the FastMCP server
mcp = FastMCP(
    name="devrev_mcp",
    version="0.1.1",
    description="DevRev MCP Server - Provides tools for interacting with DevRev API"
)

# Store DevRev resources (works, comments, etc.) for resource access
devrev_cache = {}

# @mcp.tool()
# async def search(query: str, namespace: str, ctx: Context) -> str:
#     """
#     Search DevRev using the provided query.
    
#     Args:
#         query: The search query string
#         namespace: The namespace to search in (article, issue, ticket, part, dev_user)
    
#     Returns:
#         JSON string containing search results
#     """
#     if namespace not in ["article", "issue", "ticket", "part", "dev_user"]:
#         raise ValueError(f"Invalid namespace '{namespace}'. Must be one of: article, issue, ticket, part, dev_user")
    
#     try:
#         await ctx.info(f"Searching DevRev for '{query}' in namespace '{namespace}'")
        
#         response = make_devrev_request(
#             "search.hybrid",
#             {"query": query, "namespace": namespace}
#         )
        
#         if response.status_code != 200:
#             error_text = response.text
#             await ctx.error(f"Search failed with status {response.status_code}: {error_text}")
#             raise ValueError(f"Search failed with status {response.status_code}: {error_text}")
        
#         search_results = response.json()
#         await ctx.info(f"Search completed successfully with {len(search_results.get('results', []))} results")
        
#         return json.dumps(search_results, indent=2)
    
#     except Exception as e:
#         await ctx.error(f"Search operation failed: {str(e)}")
#         raise

# @mcp.tool()
# async def create_object(
#     type: str,
#     title: str, 
#     applies_to_part: str,
#     body: str = "",
#     owned_by: list[str] = None,
#     ctx: Context = None
# ) -> str:
#     """
#     Create a new issue or ticket in DevRev.
    
#     Args:
#         type: The type of object to create ("issue" or "ticket")
#         title: The title/summary of the object
#         applies_to_part: The part ID this object applies to
#         body: The body/description of the object (optional)
#         owned_by: List of user IDs who should own this object (optional)
    
#     Returns:
#         JSON string containing the created object information
#     """
#     if type not in ["issue", "ticket"]:
#         raise ValueError(f"Invalid type '{type}'. Must be 'issue' or 'ticket'")
    
#     try:
#         await ctx.info(f"Creating new {type}: {title}")
        
#         payload = {
#             "type": type,
#             "title": title,
#             "applies_to_part": applies_to_part
#         }
        
#         if body:
#             payload["body"] = body
#         if owned_by:
#             payload["owned_by"] = owned_by
        
#         response = make_devrev_request("works.create", payload)
        
#         if response.status_code != 200:
#             error_text = response.text
#             await ctx.error(f"Failed to create {type}: HTTP {response.status_code} - {error_text}")
#             raise ValueError(f"Failed to create {type} (HTTP {response.status_code}): {error_text}")
        
#         result_data = response.json()
#         await ctx.info(f"Successfully created {type} with ID: {result_data.get('work', {}).get('id', 'unknown')}")
        
#         return json.dumps(result_data, indent=2)
        
#     except Exception as e:
#         await ctx.error(f"Failed to create {type}: {str(e)}")
#         raise

# @mcp.tool()
# async def update_object(
#     id: str,
#     type: str,
#     title: str = None,
#     body: str = None,
#     ctx: Context = None
# ) -> str:
#     """
#     Update an existing issue or ticket in DevRev.
    
#     Args:
#         id: The ID of the object to update
#         type: The type of object ("issue" or "ticket")
#         title: New title for the object (optional)
#         body: New body/description for the object (optional)
    
#     Returns:
#         JSON string containing the updated object information
#     """
#     if type not in ["issue", "ticket"]:
#         raise ValueError(f"Invalid type '{type}'. Must be 'issue' or 'ticket'")
    
#     if not title and not body:
#         raise ValueError("At least one of 'title' or 'body' must be provided for update")
    
#     try:
#         await ctx.info(f"Updating {type} {id}")
        
#         payload = {
#             "id": id,
#             "type": type
#         }
        
#         if title:
#             payload["title"] = title
#         if body:
#             payload["body"] = body
        
#         response = make_devrev_request("works.update", payload)
        
#         if response.status_code != 200:
#             error_text = response.text
#             await ctx.error(f"Failed to update {type}: HTTP {response.status_code} - {error_text}")
#             raise ValueError(f"Failed to update {type} (HTTP {response.status_code}): {error_text}")
        
#         result_data = response.json()
        
#         # Update cache if we have this object cached
#         if id in devrev_cache:
#             del devrev_cache[id]
#             await ctx.info(f"Cleared cache for updated object: {id}")
        
#         await ctx.info(f"Successfully updated {type}: {id}")
#         return json.dumps(result_data, indent=2)
        
#     except Exception as e:
#         await ctx.error(f"Failed to update {type}: {str(e)}")
#         raise

@mcp.tool()
async def get_object(id: str, ctx: Context) -> str:
    """
    Get all information about a DevRev issue and ticket using its ID.
    
    Args:
        id: The DevRev object ID
    
    Returns:
        JSON string containing the object information
    """
    try:
        await ctx.info(f"Fetching object {id} from DevRev")
        
        response = make_devrev_request("works.get", {"id": id})
        
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

# Add dynamic resource access for DevRev objects
@mcp.resource(
    uri="devrev://{id}",
    description="Access any DevRev object (tickets, comments, issues, etc.) by its full DevRev ID.",
    tags=["devrev_resource"]
)
async def get_devrev_resource(id: str, ctx: Context) -> str:
    """
    Access any DevRev object (tickets, comments, issues, etc.) by its full DevRev ID.
    
    Args:
        id: The DevRev object ID
    
    Returns:
        JSON string containing the object data
    """
    try:
        # Check cache first
        if id in devrev_cache:
            await ctx.info(f"Retrieved resource {id} from cache")
            return devrev_cache[id]
        
        # If not cached, fetch using get_object tool logic
        await ctx.info(f"Fetching resource {id} from DevRev API")
        # Handle special cases for tickets and comments
        if ":ticket/" in id:
            if ":comment/" in id:
                # For comments, use timeline-entries.get endpoint
                await ctx.info(f"Fetching comment {id}")
                response = make_devrev_request(
                    "timeline-entries.get",
                    {"id": id}
                )
            else:
                # For tickets, first get the ticket details
                ticket_id = f"TKT-{id.split(':ticket/')[1]}"
                await ctx.info(f"Fetching ticket {ticket_id}")
                response = make_devrev_request(
                    "works.get", 
                    {"id": ticket_id}
                )

                # Then get all comments via timeline entries
                timeline_response = make_devrev_request(
                    "timeline-entries.list",
                    {"object": ticket_id}
                )

                if timeline_response.status_code == 200:
                    # Merge timeline entries into ticket response
                    result = response.json()
                    result["timeline_entries"] = timeline_response.json().get("timeline_entries", [])
                    devrev_cache[id] = json.dumps(result, indent=2)
                    return devrev_cache[id]

            if response.status_code != 200:
                error_text = response.text
                await ctx.error(f"Failed to fetch {id}: HTTP {response.status_code} - {error_text}")
                raise ValueError(f"Failed to fetch {id} (HTTP {response.status_code}): {error_text}")

            result = response.json()
            devrev_cache[id] = json.dumps(result, indent=2)
            return devrev_cache[id]
        
        return await get_object(id, ctx)
        
    except Exception as e:
        await ctx.error(f"Failed to get resource {id}: {str(e)}")
        raise ValueError(f"Resource {id} not found in cache and could not be fetched: {str(e)}")

@mcp.tool(
    name="get_timeline_entries",
    description="Get all timeline entries for a DevRev ticket using its ID. <don:core:dvrv-us-1:devo/<your-org-id>:ticket/12345>",
    tags=["timeline_entries"]
)
async def get_timeline_entries(id: str, ctx: Context) -> str:
    """
    Get all timeline entries for a DevRev ticket using its ID. The API response provided by the 
    
    Args:
        id: The DevRev ticket ID - don:core:dvrv-us-1:devo/<your-org-id>:ticket/12345
    """
    try:
        await ctx.info(f"Fetching timeline entries for ticket {id}")
        
        content_list = await ctx.read_resource(id)
        if not content_list:
            return "No timeline entries found"
        
        return content_list
    except Exception as e:
        return f"Failed to get timeline entries for ticket {id}: {str(e)}"

def main():
    """Main entry point for the DevRev MCP server."""
    # Print debug message
    print(DEBUG_MESSAGE)
    
    # Run the server
    mcp.run()

if __name__ == "__main__":
    main()
