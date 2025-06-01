"""
DevRev Get Timeline Entries Tool

Provides a tool for fetching timeline entries for DevRev tickets with flexible formatting.
"""

import json
from fastmcp import Context
from ..debug import debug_error_handler


@debug_error_handler
async def get_timeline_entries(
    id: str, 
    ctx: Context, 
    format: str = "summary"
) -> str:
    """
    Get timeline entries for a DevRev ticket with flexible formatting options.
    
    Args:
        id: The DevRev ticket ID - accepts TKT-12345, 12345, or full don:core format
        ctx: FastMCP context
        format: Output format - "summary" (key info), "detailed" (conversation focus), or "full" (complete data)
    
    Returns:
        Formatted timeline entries based on the requested format
    """
    try:
        # Normalize the ticket ID to just the number
        ticket_id = _normalize_ticket_id(id)
        await ctx.info(f"Fetching timeline entries for ticket {ticket_id} in {format} format")
        
        # Use the resource URI to get the enriched timeline
        resource_uri = f"devrev://tickets/{ticket_id}/timeline"
        try:
            content = await ctx.read_resource(resource_uri)
        except Exception as resource_error:
            await ctx.error(f"Error reading resource {resource_uri}: {str(resource_error)}")
            raise resource_error
        
        if not content:
            return f"No timeline entries found for ticket {ticket_id}"
        
        # Handle the resource response - FastMCP can return different structures
        # Extract the actual timeline data from the response
        if isinstance(content, list) and len(content) > 0:
            # It's a list, likely containing a ReadResourceContents object
            first_item = content[0]
            if hasattr(first_item, 'content'):
                # ReadResourceContents object
                try:
                    timeline_data = json.loads(first_item.content)
                except (json.JSONDecodeError, AttributeError):
                    if format == "full":
                        return str(first_item.content) if hasattr(first_item, 'content') else str(first_item)
                    else:
                        return f"Error: Could not parse timeline data for ticket {ticket_id}"
            else:
                # Direct data in the list
                timeline_data = first_item
        elif hasattr(content, 'content'):
            # It's a ReadResourceContents object, get the content
            try:
                timeline_data = json.loads(content.content)
            except (json.JSONDecodeError, AttributeError):
                if format == "full":
                    return str(content.content) if hasattr(content, 'content') else str(content)
                else:
                    return f"Error: Could not parse timeline data for ticket {ticket_id}"
        elif isinstance(content, str):
            try:
                timeline_data = json.loads(content)
            except json.JSONDecodeError:
                # If it's already a string, return as-is for full format
                if format == "full":
                    return content
                else:
                    return f"Error: Could not parse timeline data for ticket {ticket_id}"
        else:
            # Content is already parsed (dict, list, etc.)
            timeline_data = content
        
        # Debug: Check what we actually received
        await ctx.info(f"DEBUG: timeline_data type: {type(timeline_data)}")
        if isinstance(timeline_data, dict):
            await ctx.info(f"DEBUG: timeline_data keys: {list(timeline_data.keys())}")
        elif isinstance(timeline_data, list):
            await ctx.info(f"DEBUG: timeline_data length: {len(timeline_data)}")
            if timeline_data:
                await ctx.info(f"DEBUG: first item type: {type(timeline_data[0])}")
        
        # Format based on requested type
        if format == "summary":
            return _format_summary(timeline_data, ticket_id)
        elif format == "detailed":
            return _format_detailed(timeline_data, ticket_id)
        else:  # format == "full"
            try:
                return json.dumps(timeline_data, indent=2, default=str)
            except (TypeError, ValueError) as e:
                await ctx.error(f"Could not serialize timeline data to JSON: {str(e)}")
                return str(timeline_data)
            
    except Exception as e:
        await ctx.error(f"Failed to get timeline entries for {id}: {str(e)}")
        return f"Failed to get timeline entries for ticket {id}: {str(e)}"


def _normalize_ticket_id(id: str) -> str:
    """
    Normalize various ticket ID formats to just the numeric ID.
    
    Accepts:
    - TKT-12345 -> 12345
    - tkt-12345 -> 12345
    - don:core:dvrv-us-1:devo/118WAPdKBc:ticket/12345 -> 12345
    - 12345 -> 12345
    """
    if id.startswith("don:core:") and ":ticket/" in id:
        # Extract from full DevRev ID
        return id.split(":ticket/")[1]
    elif id.upper().startswith("TKT-"):
        # Extract from TKT- format (case insensitive)
        return id[4:]  # Remove first 4 characters (TKT- or tkt-)
    else:
        # Assume it's already just the ticket number
        return id


def _format_summary(timeline_data, ticket_id: str) -> str:
    """
    Format timeline data as a concise summary focusing on key metrics and latest activity.
    """
    # Handle both dict and list formats
    if isinstance(timeline_data, list):
        # If it's a list, treat it as the conversation thread
        conversation = timeline_data
        summary = {}
    else:
        # If it's a dict, extract the expected fields
        summary = timeline_data.get("summary", {})
        conversation = timeline_data.get("conversation_thread", [])
    
    # Build summary text
    lines = [
        f"**TKT-{ticket_id} Timeline Summary:**",
        "",
        f"**Subject:** {summary.get('subject', 'Unknown')}",
        f"**Status:** {summary.get('current_stage', 'Unknown')}",
        f"**Customer:** {summary.get('customer', 'Unknown')}",
        f"**Created:** {summary.get('created_date', 'Unknown')}",
    ]
    
    # Add message counts
    customer_messages = [msg for msg in conversation if msg.get("speaker", {}).get("type") == "customer"]
    support_messages = [msg for msg in conversation if msg.get("speaker", {}).get("type") == "support"]
    
    lines.extend([
        "",
        f"**Activity:** {len(customer_messages)} customer messages, {len(support_messages)} support responses",
    ])
    
    # Add last activity timestamps
    if summary.get("last_customer_message"):
        lines.append(f"**Last customer message:** {summary['last_customer_message']}")
    if summary.get("last_support_response"):
        lines.append(f"**Last support response:** {summary['last_support_response']}")
    
    # Add latest messages preview
    if conversation:
        lines.extend([
            "",
            "**Recent Activity:**"
        ])
        
        # Show last 3 messages
        recent_messages = conversation[-3:] if len(conversation) > 3 else conversation
        for msg in recent_messages:
            speaker = msg.get("speaker", {})
            timestamp = msg.get("timestamp", "")[:10]  # Just date part
            message_preview = msg.get("message", "")[:100] + ("..." if len(msg.get("message", "")) > 100 else "")
            lines.append(f"- **{speaker.get('name', 'Unknown')}** ({timestamp}): {message_preview}")
    
    # Add artifacts info
    if isinstance(timeline_data, dict):
        artifacts = timeline_data.get("all_artifacts", [])
        if artifacts:
            lines.extend([
                "",
                f"**Attachments:** {len(artifacts)} file(s) attached"
            ])
    
    return "\n".join(lines)


def _format_detailed(timeline_data, ticket_id: str) -> str:
    """
    Format timeline data with focus on conversation flow and key events.
    """
    # Handle both dict and list formats
    if isinstance(timeline_data, list):
        # If it's a list, treat it as the conversation thread
        conversation = timeline_data
        summary = {}
    else:
        # If it's a dict, extract the expected fields
        summary = timeline_data.get("summary", {})
        conversation = timeline_data.get("conversation_thread", [])
    
    lines = [
        f"**TKT-{ticket_id} Detailed Timeline:**",
        "",
        f"**Subject:** {summary.get('subject', 'Unknown')}",
        f"**Status:** {summary.get('current_stage', 'Unknown')}",
        f"**Customer:** {summary.get('customer', 'Unknown')}",
        "",
        "**Conversation Thread:**"
    ]
    
    # Add each conversation entry
    for msg in conversation:
        speaker = msg.get("speaker", {})
        timestamp = msg.get("timestamp", "")
        message = msg.get("message", "")
        artifacts = msg.get("artifacts", [])
        
        # Format timestamp to be more readable
        display_time = timestamp[:19].replace("T", " ") if timestamp else "Unknown time"
        
        lines.extend([
            "",
            f"**{msg.get('seq', '?')}. {speaker.get('name', 'Unknown')} ({speaker.get('type', 'unknown')}) - {display_time}**"
        ])
        
        # Add message content with proper formatting
        if message:
            # Handle multi-line messages by indenting them
            message_lines = message.split("\n")
            for line in message_lines:
                if line.strip():
                    lines.append(f"   {line}")
                else:
                    lines.append("")
        
        # Add artifacts info
        if artifacts:
            lines.append(f"   *Attachments: {len(artifacts)} file(s)*")
    
    # Add key events summary
    if isinstance(timeline_data, dict):
        key_events = timeline_data.get("key_events", [])
        if key_events:
            lines.extend([
                "",
                "**Key Events:**"
            ])
            for event in key_events[-5:]:  # Show last 5 events
                event_time = event.get("timestamp", "")[:19].replace("T", " ")
                event_type = event.get("type", "unknown")
                actor = event.get("actor", {}).get("name", "System")
                lines.append(f"- {event_time}: {event_type} by {actor}")
    
    return "\n".join(lines)