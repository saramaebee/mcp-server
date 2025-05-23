"""
Copyright (c) 2025 DevRev, Inc.
SPDX-License-Identifier: MIT

This module implements the MCP server for DevRev integration.
"""

import asyncio
import os
import requests

from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl
import mcp.server.stdio
from .utils import make_devrev_request
from .utils import make_internal_devrev_request

server = Server("devrev_mcp")

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List available tools.
    Each tool specifies its arguments using JSON Schema validation.
    """

    return [
        types.Tool(
            name="get_current_user",
            description="Fetch the current DevRev user’s ID. Use this to set the `owned_by` field when creating or updating an issue or ticket.",
            inputSchema={"type": "object", "properties": {}},
        ),

        types.Tool(
            name="get_git_diff_for_title_and_body",
            description="Get the git diff between main and HEAD for a given repo path to generate a title and body for a issue or ticket (for both creating and updating) describing the code changes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "repo_path": {
                        "type": "string",
                        "description": "Absolute path to the local git repository"
                    }
                },
                "required": ["repo_path"]
            },
        ),

        types.Tool(
            name="find_relevant_part",
            description="Search for a DevRev Part based on an issue title. Use this to determine the `applies_to_part` when creating or updating a work object.",
            inputSchema={
                "type": "object",
                "properties": {"title": {"type": "string", "description": "The title of the issue or ticket to search for."}},
                "required": ["title"],
            },
        ),

        types.Tool(
            name="search",
            description="Search DevRev for work objects, articles, parts, or users using a text query. Use this to look up existing records.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "namespace": {
                        "type": "string",
                        "enum": ["article", "issue", "ticket", "part", "dev_user"],
                        "description": "The namespace to search in. Use this to specify the type of object you want to search for."
                    },
                },
                "required": ["query", "namespace"],
            },
        ),

        types.Tool(
            name="get_object",
            description="Fetch complete details for a DevRev issue or ticket using its unique ID. Use this when you need full context about a specific work object.",
            inputSchema={
                "type": "object",
                "properties": {"id": {"type": "string", "description": "The ID of the issue or ticket to get the details for."}},
                "required": ["id"],
            },
        ),

        types.Tool(
            name="create_object",
            description="Create a new DevRev issue or ticket. Requires a title, part ID, and optionally a body and owners. Recommended flow: get git diff → find part → get user → call this tool.",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["issue", "ticket"]},
                    "title": {"type": "string", "description": "The title of the issue or ticket to create. When the title is not provided in query, the tool will use the latest git diff to generate a title."},
                    "body": {"type": "string", "description": "The body of the issue or ticket to create. When the body is not provided in query, the tool will use the latest git diff to generate a body."},
                    "applies_to_part": {"type": "string", "description": "The part ID to associate the issue or ticket with. When the part ID is not provided in query, the tool will use the find_relevant_part tool to generate a part ID."},
                    "owned_by": {"type": "array", "items": {"type": "string"}, "description": "The list of user IDs to associate the issue or ticket with. When the owner is not provided in query, the tool will use the get_current_user tool to generate a list of user IDs."},
                },
                "required": ["type", "title", "body", "applies_to_part", "owned_by"],
            },
        ),

        types.Tool(
            name="update_object",
            description="Update an existing issue or ticket. Use this to change the title, body, owner, stage, or sprint after its creation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["issue", "ticket"]},
                    "id": {"type": "string"},
                    "title": {"type": "string", "description": "The title of the issue or ticket to update. When the title is not provided in query, the tool will use the latest git diff to generate a title."},
                    "body": {"type": "string", "description": "The body of the issue or ticket to update. When the body is not provided in query, the tool will use the latest git diff to generate a body."},
                    "owned_by": {"type": "array", "items": {"type": "string"}, "description": "The list of user IDs to associate the issue or ticket with. When the owner is not provided in query, the tool will use the get_current_user tool to generate a list of user IDs."},
                    "stage": {"type": "string", "description": "The stage ID to associate the issue or ticket with. When the stage is not provided in query, the tool will use the valid_stage_transitions tool to generate a stage ID."},
                    "sprint": {"type": "string", "description": "The sprint ID to associate the issue or ticket with. When the sprint is not provided in query, the tool will use the get_sprints tool to generate a sprint ID."},
                },
                "required": ["id", "type"],
            },
        ),

        types.Tool(
            name="valid_stage_transitions",
            description="List all valid stage transitions for the current stage of a work object. Use this before changing an issue or ticket’s stage.",
            inputSchema={
                "type": "object",
                "properties": {"id": {"type": "string", "description": "The ID of the issue or ticket to get the valid stage transitions for."}},
                "required": ["id"],
            },
        ),

        types.Tool(
            name="get_sprints",
            description="Retrieve active or planned sprints for a given DevRev part. Use this to associate a work object with an active sprint.",
            inputSchema={
                "type": "object",
                "properties": {
                    "ancestor_part_id": {"type": "string", "description": "The ID of the part to get the sprints for."},
                    "state": {
                        "type": "string",
                        "enum": ["active", "planned"],
                        "description": "The state of the sprints to get. When the state is not provided in query, the tool will get the active sprints."
                    },
                },
                "required": ["ancestor_part_id"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict | None
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    """
    Handle tool execution requests.
    Tools can modify server state and notify clients of changes.
    """
    if name == "search":
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
                    text=f"Search failed witssh status new {response.status_code}: {error_text}"
                )
            ]
        
        search_results = response.json()
        return [
            types.TextContent(
                type="text",
                text=f"Search results for '{query}':\n{search_results}"
            )
        ]

    elif name == "get_git_diff_for_title_and_body":
        import subprocess
        repo_path = arguments["repo_path"]

        try:
            diff_output = subprocess.check_output(
                ["git", "diff", "main...HEAD"],
                cwd=repo_path,
                stderr=subprocess.STDOUT
            ).decode("utf-8")
        except subprocess.CalledProcessError as e:
            return [ types.TextContent(type="text", text=f"git diff failed: {e.output.decode()}") ]

        if not diff_output.strip():
            return [ types.TextContent(type="text", text="No changes between main and HEAD.") ]

        return [ types.TextContent(type="text", text=diff_output) ]

    
    elif name == "find_relevant_part":
        if not arguments:
            raise ValueError("Missing arguments")

        title = arguments.get("title")
        if not title:
            raise ValueError("title is required.")

        query_text = f"{title}"

        response = make_devrev_request(
            "search.hybrid",
            {
                "query": query_text,
                "namespace": "part"
            }
        )

        if response.status_code != 200:
            error_text = response.text
            return [
                types.TextContent(
                    type="text",
                    text=f"Search for relevant parts failed with status {response.status_code}: {error_text}"
                )
            ]

        results = response.json()

        return [
            types.TextContent(
                type="text",
                text=f"Relevant parts for the given issue description:\n{results}"
            )
        ]
    elif name == "get_current_user":
        response = make_devrev_request(
            "dev-users.self",
            {}
        )

        if response.status_code != 200:
            error_text = response.text
            return [
                types.TextContent(
                    type="text",
                    text=f"Get current user failed with status {response.status_code}: {error_text}"
                )
            ]

        user_info = response.json()
        user_id = user_info.get("dev_user", {}).get("id")

        return [
            types.TextContent(
                type="text",
                text=f"Current DevRev user ID: {user_id}"
            )
        ]
    elif name == "get_object":
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
                    text=f"Get object failed with status {response.status_code}: {error_text}"
                )
            ]
        
        object_info = response.json()
        return [
            types.TextContent(
                type="text",
                text=f"Object information for '{id}':\n{object_info}"
            )
        ]
    elif name == "create_object":
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
                    text=f"Create object failed with status {response.status_code}: {error_text}"
                )
            ]

        return [
            types.TextContent(
                type="text",
                text=f"Object created successfully: {response.json()}"
            )
        ]
    elif name == "update_object":
        # Update mandatory fields
        if not arguments:
            raise ValueError("Missing arguments")

        id = arguments.get("id")
        if not id:
            raise ValueError("Missing id parameter")
        
        object_type = arguments.get("type")
        if not object_type:
            raise ValueError("Missing type parameter")
        
        title = arguments.get("title")
        body = arguments.get("body")
        stage = arguments.get("stage")
        sprint = arguments.get("sprint")
        owned_by = arguments.get("owned_by")

        # Build request payload with only the fields that have values
        update_payload = {"id": id, "type": object_type}
        if title:
            update_payload["title"] = title
        if body:
            update_payload["body"] = body
        if stage:
            update_payload["stage"] = {"stage": stage}
        if sprint:
            update_payload["sprint"] = sprint
        if owned_by:
            update_payload["owned_by"] = owned_by

        # Make devrev request to update the object
        response = make_devrev_request(
            "works.update",
            update_payload
        )

        # Check if the request was successful
        if response.status_code != 200:
            error_text = response.text
            return [
                types.TextContent(
                    type="text",
                    text=f"Update object failed with status {response.status_code}: {error_text}"
                )
            ]
        
        return [
            types.TextContent(
                type="text",
                text=f"Object updated successfully: {id}"
            )
        ]
    elif name == "valid_stage_transitions":
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
                    text=f"Get object for Get stage transitions failed with status {response.status_code}: {error_text}"
                )
            ]
        
        current_stage_id = response.json().get("work", {}).get("stage", {}).get("stage", {}).get("id", {})

        stock_schema_frag_id = response.json().get("work", {}).get("stock_schema_fragment", {})
        custom_schema_frag_id = response.json().get("work", {}).get("custom_schema_fragments", [])
        leaf_type = response.json().get("work", {}).get("type", {})

        schema_response = make_internal_devrev_request(
            "schemas.aggregated.get",
            {
             "custom_schema_fragment_ids": custom_schema_frag_id,
             "leaf_type": leaf_type,
             "stock_schema_fragment_id": stock_schema_frag_id
            }
        )

        if schema_response.status_code != 200:
            error_text = schema_response.text
            return [
                types.TextContent(
                    type="text",
                    text=f"Get object schema for Get stage transitions failed with status {schema_response.status_code}: {error_text}"
                )
            ]

        stage_diagram_id = schema_response.json().get("schema", {}).get("stage_diagram_id", {}).get("id", {})
        stage_transitions_response = make_internal_devrev_request(
            "stage-diagrams.get",
            {"id": stage_diagram_id}
        )

        if stage_transitions_response.status_code != 200:
            error_text = stage_transitions_response.text
            return [
                types.TextContent(
                    type="text",
                    text=f"Get stage diagram for Get stage transitions failed with status {stage_transitions_response.status_code}: {error_text}"
                )
            ]

        # Need to iterate over the stages and find the one which matches current stage id and return its transitions
        stages = stage_transitions_response.json().get("stage_diagram", {}).get("stages", [])

        for stage in stages:
            if stage.get("stage", {}).get("id") == current_stage_id:
                transitions = stage.get("transitions", [])
                return [
                    types.TextContent(
                        type="text",
                        text=f"Valid Transitions for '{id}' from current stage:\n{transitions}"
                    )
                ]

        return [
            types.TextContent(
                type="text",
                text=f"No valid transitions found for '{id}' from current stage"
            ),
        ]
    elif name == "get_sprints":
        if not arguments:
            raise ValueError("Missing arguments")

        ancestor_part_id = arguments.get("ancestor_part_id")
        if not ancestor_part_id:
            raise ValueError("Missing ancestor_part_id parameter")

        state = arguments.get("state")
        if not state:
            state = "active"
        
        response = make_internal_devrev_request(
            "vistas.groups.list",
            {
                "ancestor_part": [ancestor_part_id],
                "group_object_type": ["work"],
                "state": [state]
            }
        )
        
        if response.status_code != 200:
            error_text = response.text
            return [
                types.TextContent(
                    type="text",
                    text=f"Get sprints failed with status {response.status_code}: {error_text}"
                )
            ]
        
        sprints = response.json().get("vista_group", [])
        return [
            types.TextContent(
                type="text",
                text=f"'{state}' Sprints for '{ancestor_part_id}':\n{sprints}"
            )
        ]
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
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
