"""
Create work tool for DevRev MCP server.
"""

import json
from typing import Dict, Any, List
import mcp.types as types
from .base import BaseTool
from ..utils import make_devrev_request


class CreateWorkTool(BaseTool):
    """Tool for creating a new issue or ticket in DevRev."""
    
    def __init__(self):
        # Reference to the cache - will be set by the server
        self.devrev_cache = None
    
    def set_cache(self, cache: Dict[str, str]):
        """Set the cache reference from the server."""
        self.devrev_cache = cache
    
    @property
    def name(self) -> str:
        return "create_work"
    
    @property
    def description(self) -> str:
        return "Create a new isssue or ticket in DevRev"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["issue", "ticket"]},
                "title": {"type": "string"},
                "body": {"type": "string"},
                "applies_to_part": {"type": "string"},
                "owned_by": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["type", "title", "applies_to_part"],
        }
    
    async def _execute_impl(self, arguments: Dict[str, Any] | None) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
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
        if self.devrev_cache is not None and 'work' in created_work and 'id' in created_work['work']:
            work_id = created_work['work']['id']
            self.devrev_cache[work_id] = json.dumps(created_work['work'])
        
        return [
            types.TextContent(
                type="text",
                text=f"Work created successfully: {created_work}"
            )
        ] 