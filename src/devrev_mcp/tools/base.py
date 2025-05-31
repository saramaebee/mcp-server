"""
Base tool class for DevRev MCP server tools.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List

import mcp.types as types
from ..debug import debug_error_handler


class BaseTool(ABC):
    """
    Abstract base class for all DevRev MCP tools.
    
    Each tool must implement:
    - name: The tool's unique identifier
    - description: Human-readable description of what the tool does
    - input_schema: JSON Schema for validating tool arguments
    - execute: The actual tool logic
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the tool's unique name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Return a description of what this tool does."""
        pass
    
    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """Return the JSON Schema for validating tool arguments."""
        pass
    
    @debug_error_handler
    async def execute(self, arguments: Dict[str, Any] | None) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """
        Execute the tool with the given arguments.
        This method is automatically wrapped with error handling.
        """
        return await self._execute_impl(arguments)
    
    @abstractmethod
    async def _execute_impl(self, arguments: Dict[str, Any] | None) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """
        Internal implementation of the tool logic.
        Subclasses should implement this method instead of execute().
        """
        pass
    
    def to_mcp_tool(self) -> types.Tool:
        """Convert this tool to an MCP Tool object for registration."""
        return types.Tool(
            name=self.name,
            description=self.description,
            inputSchema=self.input_schema
        ) 