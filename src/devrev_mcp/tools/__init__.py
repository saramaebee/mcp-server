"""
Tools package for DevRev MCP server.
This module automatically discovers and registers all available tools.
"""

from .base import BaseTool
from .search import SearchTool
from .get_work import GetWorkTool
from .create_work import CreateWorkTool
from .get_timeline_entries import GetTimelineEntresTool

# Registry of all available tools
TOOLS = [
    SearchTool(),
    GetWorkTool(),
    CreateWorkTool(),
    GetTimelineEntresTool(),
]

# Create a mapping for easy tool lookup by name
TOOL_MAP = {tool.name: tool for tool in TOOLS}

__all__ = ['BaseTool', 'TOOLS', 'TOOL_MAP'] 