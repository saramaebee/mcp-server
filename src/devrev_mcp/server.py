"""
Copyright (c) 2025 DevRev, Inc.
SPDX-License-Identifier: MIT

This module implements the MCP server for DevRev integration.
"""

import json
import os
from pathlib import Path

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio
from .utils import make_devrev_request
from .tools import TOOLS, TOOL_MAP
from .debug import debug_error_handler

server = Server("devrev_mcp")

# Store DevRev resources (works, comments, etc.) for resource access
devrev_cache = {}

# Check debug mode and store state
DEBUG_ENABLED = os.environ.get("DRMCP_DEBUG") == "1"
DEBUG_MESSAGE = "🐛 DEBUG MODE ENABLED - sara wuz here" if DEBUG_ENABLED else "🐛 DEBUG MODE DISABLED - sara wuz here"

# Initialize tools with cache access
for tool in TOOLS:
    if hasattr(tool, 'set_cache'):
        tool.set_cache(devrev_cache)

@server.list_tools()
@debug_error_handler
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """
    return [tool.to_mcp_tool() for tool in TOOLS]

@server.list_resources()
@debug_error_handler
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
@debug_error_handler
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
            # For work items, we can fetch them directly
            try:
                response = make_devrev_request("works.get", {"id": resource_id})
                if response.status_code == 200:
                    resource_data = response.json()
                    devrev_cache[resource_id] = json.dumps(resource_data)
                    return json.dumps(resource_data)
                else:
                    raise ValueError(f"Resource {resource_id} not found or inaccessible")
            except Exception as e:
                raise ValueError(f"Resource {resource_id} not found in cache and could not be fetched: {str(e)}")
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
    if name in TOOL_MAP:
        tool = TOOL_MAP[name]
        return await tool.execute(arguments)
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
