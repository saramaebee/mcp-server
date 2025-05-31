"""
Search tool for DevRev MCP server.
"""

from typing import Dict, Any, List
import mcp.types as types
from .base import BaseTool
from ..utils import make_devrev_request


class SearchTool(BaseTool):
    """Tool for searching DevRev using the provided query."""
    
    @property
    def name(self) -> str:
        return "search"
    
    @property
    def description(self) -> str:
        return "Search DevRev using the provided query"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "namespace": {"type": "string", "enum": ["article", "issue", "ticket", "part", "dev_user"]},
            },
            "required": ["query", "namespace"],
        }
    
    async def _execute_impl(self, arguments: Dict[str, Any] | None) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
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