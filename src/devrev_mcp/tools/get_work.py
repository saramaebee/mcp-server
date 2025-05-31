"""
Get work tool for DevRev MCP server.
"""

import json
from typing import Dict, Any, List
import mcp.types as types
from .base import BaseTool
from ..utils import make_devrev_request


class GetWorkTool(BaseTool):
    """Tool for getting information about a DevRev issue and ticket using its ID."""
    
    def __init__(self):
        # Reference to the cache - will be set by the server
        self.devrev_cache = None
    
    def set_cache(self, cache: Dict[str, str]):
        """Set the cache reference from the server."""
        self.devrev_cache = cache
    
    @property
    def name(self) -> str:
        return "get_work"
    
    @property
    def description(self) -> str:
        return "Get all information about a DevRev issue and ticket using its ID"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
            },
            "required": ["id"],
        }
    
    async def _execute_impl(self, arguments: Dict[str, Any] | None) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
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
        if self.devrev_cache is not None:
            self.devrev_cache[id] = json.dumps(object_info)
        
        return [
            types.TextContent(
                type="text",
                text=f"Work information for '{id}':\n{object_info}"
            )
        ] 