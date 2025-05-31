"""
Copyright (c) 2025 DevRev, Inc.
SPDX-License-Identifier: MIT

This module implements the MCP server for DevRev integration.
"""

import asyncio
import os
import requests
import json
import traceback
from functools import wraps

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio
from .utils import make_devrev_request

server = Server("devrev_mcp")

# Store DevRev resources (works, comments, etc.) for resource access
devrev_cache = {}

# Check debug mode and store state
DEBUG_ENABLED = os.environ.get("DRMCP_DEBUG") == "1"
DEBUG_MESSAGE = "🐛 DEBUG MODE ENABLED - sara wuz here" if DEBUG_ENABLED else "🐛 DEBUG MODE DISABLED - sara wuz here"

def debug_error_handler(func):
    """
    Decorator that catches exceptions in MCP tools and returns detailed debug information
    as the tool response when DRMCP_DEBUG=1.
    """
    debug_enabled = DEBUG_ENABLED
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            # Add debug message to all tool responses when debug is enabled
            if debug_enabled and result:
                # Add debug message as first item in response
                debug_content = types.TextContent(
                    type="text", 
                    text=f"{DEBUG_MESSAGE}\n\n"
                )
                if isinstance(result, list) and len(result) > 0 and hasattr(result[0], 'text'):
                    result[0].text = debug_content.text + result[0].text
                else:
                    result.insert(0, debug_content)
            return result
        except Exception as e:
            if debug_enabled:
                # Debug mode: return detailed error information
                error_message = f"""ERROR (Debug Mode): {type(e).__name__}: {str(e)}

Full traceback:
{traceback.format_exc()}

This is a debug error response. Let's troubleshoot this together.

{DEBUG_MESSAGE}"""
            else:
                # Production mode: return generic error message
                error_message = f"An error occurred while executing the tool. Please try again or contact support."
            
            return [
                types.TextContent(
                    type="text",
                    text=error_message
                )
            ]
    
    return wrapper

@debug_error_handler
async def search_tool(arguments: dict | None) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle search tool execution."""
    if not arguments:
        raise ValueError("Missing arguments")

    query = arguments.get("query")
    if not query:
        raise ValueError("Missing query parameter")
    
    namespace = arguments.get("namespace")
    if not namespace:
        raise ValueError("Missing namespace parameter")

    response = make_devrev_request(
        "search.hybrid",
        {"query": query, "namespace": namespace}
    )
    if response.status_code != 200:
        error_text = response.text
        return [
            types.TextContent(
                type="text",
                text=f"Search failed with status {response.status_code}: {error_text}"
            )
        ]
    
    search_results = response.json()
    return [
        types.TextContent(
            type="text",
            text=f"Search results for '{query}':\n{search_results}"
        )
    ]

@debug_error_handler
async def get_work_tool(arguments: dict | None) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle get_work tool execution."""
    if not arguments:
        raise ValueError("Missing arguments")

    id = arguments.get("id")
    if not id:
        raise ValueError("Missing id parameter")
    
    response = make_devrev_request(
        "works.get",
        {"id": id}
    )
    if response.status_code != 200:
        error_text = response.text
        return [
            types.TextContent(
                type="text",
                text=f"Get work failed with status {response.status_code}: {error_text}"
            )
        ]
    
    object_info = response.json()
    # Cache the work data for resource access
    devrev_cache[id] = json.dumps(object_info)
    return [
        types.TextContent(
            type="text",
            text=f"Work information for '{id}':\n{object_info}"
        )
    ]

@debug_error_handler
async def create_work_tool(arguments: dict | None) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle create_work tool execution."""
    if not arguments:
        raise ValueError("Missing arguments")

    # Mandatory fields
    object_type = arguments.get("type")
    if not object_type:
        raise ValueError("Missing type parameter")

    title = arguments.get("title")
    if not title:
        raise ValueError("Missing title parameter")

    applies_to_part = arguments.get("applies_to_part")
    if not applies_to_part:
        raise ValueError("Missing applies_to_part parameter")

    # Optional fields
    body = arguments.get("body", "")
    owned_by = arguments.get("owned_by", [])

    response = make_devrev_request(
        "works.create",
        {
            "type": object_type,
            "title": title,
            "body": body,
            "applies_to_part": applies_to_part,
            "owned_by": owned_by
        }
    )
    if response.status_code != 201:
        error_text = response.text
        return [
            types.TextContent(
                type="text",
                text=f"Create work failed with status {response.status_code}: {error_text}"
            )
        ]

    created_work = response.json()
    # Cache the created work data for resource access
    if 'work' in created_work and 'id' in created_work['work']:
        work_id = created_work['work']['id']
        devrev_cache[work_id] = json.dumps(created_work['work'])
    
    return [
        types.TextContent(
            type="text",
            text=f"Work created successfully: {created_work}"
        )
    ]

@debug_error_handler
async def get_timeline_entries_tool(arguments: dict | None) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """Handle get_timeline_entries tool execution."""
    if not arguments:
        raise ValueError("Missing arguments")

    # Debug: check arguments type
    if not isinstance(arguments, dict):
        return [
            types.TextContent(
                type="text",
                text=f"Error: arguments is not a dict but {type(arguments)}: {arguments}"
            )
        ]

    object_id = arguments.get("object_id")
    if not object_id:
        raise ValueError("Missing object_id parameter")
    
    try:
        response = make_devrev_request(
            "timeline-entries.list",
            {"object": object_id}
        )
    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=f"Error making timeline request: {e}"
            )
        ]
    if response.status_code != 200:
        error_text = response.text
        return [
            types.TextContent(
                type="text",
                text=f"Get timeline entries failed with status {response.status_code}: {error_text}"
            )
        ]
    
    timeline_data = response.json()
    
    # Cache individual timeline entries as resources and build summary
    entry_summary = []
    entry_count = 0
    if 'timeline_entries' in timeline_data:
        for i, entry in enumerate(timeline_data['timeline_entries']):
            # Debug: check entry type
            if not isinstance(entry, dict):
                return [
                    types.TextContent(
                        type="text",
                        text=f"Error: Entry {i} is not a dict but {type(entry)}: {entry}"
                    )
                ]
            if 'id' in entry:
                entry_id = entry['id']
                devrev_cache[entry_id] = json.dumps(entry)
                entry_count += 1
                
                # Add summary info for this entry
                entry_info = {
                    'id': entry_id,
                    'type': entry.get('type', 'unknown'),
                    'created_date': entry.get('created_date'),
                    'visibility': entry.get('visibility', {}).get('label', 'unknown')
                }
                
                # Add type-specific summary info
                if entry.get('type') == 'timeline_comment':
                    body_preview = entry.get('body', '')[:100] + ('...' if len(entry.get('body', '')) > 100 else '')
                    entry_info['body_preview'] = body_preview
                    entry_info['created_by'] = entry.get('created_by', {}).get('display_name', 'unknown')
                
                entry_summary.append(entry_info)
    
    summary_text = f"""Timeline entries for '{object_id}':
Total entries: {entry_count}
Entries cached as resources (access via devrev://<entry_id>):

"""
    
    for i, entry in enumerate(entry_summary[:10]):  # Show first 10 entries in summary
        summary_text += f"{i+1}. {entry['id']} ({entry['type']}) - {entry.get('created_date', 'no date')}\n"
        if 'body_preview' in entry:
            summary_text += f"   Preview: {entry['body_preview']}\n"
        if 'created_by' in entry:
            summary_text += f"   By: {entry['created_by']}\n"
        summary_text += "\n"
    
    if entry_count > 10:
        summary_text += f"... and {entry_count - 10} more entries (all available as resources)\n"
    
    return [
        types.TextContent(
            type="text",
            text=summary_text
        )
    ]

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [
        types.Tool(
            name="search",
            description="Search DevRev using the provided query",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "namespace": {"type": "string", "enum": ["article", "issue", "ticket", "part", "dev_user"]},
                },
                "required": ["query", "namespace"],
            },
        ),
        types.Tool(
            name="get_work",
            description="Get all information about a DevRev issue and ticket using its ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                },
                "required": ["id"],
            },
        ),
        types.Tool(
            name="create_work",
            description="Create a new isssue or ticket in DevRev",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["issue", "ticket"]},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "applies_to_part": {"type": "string"},
                    "owned_by": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["type", "title", "applies_to_part"],
            },
        ),
        types.Tool(
            name="get_timeline_entries",
            description="Get timeline entries for a DevRev object (ticket, issue, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_id": {"type": "string"},
                },
                "required": ["object_id"],
            },
        )
    ]

@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    """
    List available resources.
    Each resource can be accessed via the read_resource handler.
    """
    resources = []
    for resource_id in devrev_cache.keys():
        resource_data = devrev_cache[resource_id]
        if ':comment/' in resource_id:
            # Timeline comment resource
            resources.append(
                types.Resource(
                    uri=AnyUrl(f"devrev://{resource_id}"),
                    name=f"Comment {resource_id.split('/')[-1]}",
                    description=f"DevRev timeline comment {resource_id}",
                    mimeType="application/json"
                )
            )
        else:
            # Work item or other resource
            resources.append(
                types.Resource(
                    uri=AnyUrl(f"devrev://{resource_id}"),
                    name=f"DevRev {resource_id.split('/')[-2] if '/' in resource_id else 'Resource'} {resource_id.split('/')[-1] if '/' in resource_id else resource_id}",
                    description=f"DevRev resource {resource_id}",
                    mimeType="application/json"
                )
            )
    return resources

@server.read_resource()
async def handle_read_resource(uri: AnyUrl) -> str:
    """
    Read a specific resource by URI.
    """
    uri_str = str(uri)
    if uri_str.startswith("devrev://"):
        resource_id = uri_str.replace("devrev://", "")
        if resource_id in devrev_cache:
            return devrev_cache[resource_id]
        else:
            # If not in cache, try to fetch it based on resource type
            if ':comment/' in resource_id:
                # Timeline comment - cannot fetch individual comments directly
                raise ValueError(f"Timeline comment {resource_id} not found in cache")
            else:
                # Assume it's a work item
                response = make_devrev_request("works.get", {"id": resource_id})
                if response.status_code == 200:
                    resource_data = response.json()
                    devrev_cache[resource_id] = json.dumps(resource_data)
                    return json.dumps(resource_data)
                else:
                    raise ValueError(f"Resource {resource_id} not found")
    else:
        raise ValueError(f"Unknown resource URI: {uri}")

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can modify server state and notify clients of changes.
    """
    # Route to appropriate tool handler
    if name == "search":
        return await search_tool(arguments)
    elif name == "get_work":
        return await get_work_tool(arguments)
    elif name == "create_work":
        return await create_work_tool(arguments)
    elif name == "get_timeline_entries":
        return await get_timeline_entries_tool(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    # Check if debug mode is enabled and print debug message
    if DEBUG_ENABLED:
        print(DEBUG_MESSAGE)
    else:
        print(DEBUG_MESSAGE)
    
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="devrev_mcp",
                server_version="0.1.1",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )
