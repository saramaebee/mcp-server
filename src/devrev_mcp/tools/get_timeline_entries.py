"""
Get timeline entries tool for DevRev MCP server.
"""

import json
from typing import Dict, Any, List
import mcp.types as types
from .base import BaseTool
from ..utils import make_devrev_request


class GetTimelineEntresTool(BaseTool):
    """Tool for getting timeline entries for a DevRev object (ticket, issue, etc.)."""
    
    def __init__(self):
        # Reference to the cache - will be set by the server
        self.devrev_cache = None
    
    def set_cache(self, cache: Dict[str, str]):
        """Set the cache reference from the server."""
        self.devrev_cache = cache
    
    @property
    def name(self) -> str:
        return "get_timeline_entries"
    
    @property
    def description(self) -> str:
        return "Get timeline entries for a DevRev object (ticket, issue, etc.)"
    
    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object_id": {"type": "string"},
            },
            "required": ["object_id"],
        }
    
    async def _execute_impl(self, arguments: Dict[str, Any] | None) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
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
                if 'id' in entry and self.devrev_cache is not None:
                    entry_id = entry['id']
                    self.devrev_cache[entry_id] = json.dumps(entry)
                    entry_count += 1
                    
                    # Add summary info for this entry
                    entry_info = {
                        'id': entry_id,
                        'type': entry.get('type', 'unknown'),
                        'created_date': entry.get('created_date'),
                        'visibility': entry.get('visibility', {}).get('label', 'unknown') if isinstance(entry.get('visibility'), dict) else entry.get('visibility', 'unknown')
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