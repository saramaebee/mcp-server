"""
DevRev Get Timeline Entries Tool

Provides a tool for fetching timeline entries for DevRev tickets with flexible formatting.
"""

import json
from fastmcp import Context
from ..types import VisibilityInfo, TimelineEntryType
from ..error_handler import tool_error_handler
from ..utils import read_resource_content


@tool_error_handler("get_timeline_entries")
async def get_timeline_entries(
    id: str, 
    ctx: Context, 
    format: str = "summary"
) -> str:
    """
    Get timeline entries for a DevRev work item (ticket or issue) with flexible formatting options.
    
    Args:
        id: The DevRev work ID - accepts TKT-12345, ISS-9031, numeric IDs, or full don:core format
        ctx: FastMCP context
        format: Output format - "summary" (key info), "detailed" (conversation focus), or "full" (complete data)
    
    Returns:
        Formatted timeline entries based on the requested format
    """
    try:
        # Determine work item type and normalize ID
        work_type, normalized_id, display_id = _normalize_work_id(id)
        await ctx.info(f"Fetching timeline entries for {work_type} {normalized_id} in {format} format")
        
        # Use the appropriate resource URI based on work type
        if work_type == "ticket":
            resource_uri = f"devrev://tickets/{normalized_id}/timeline"
        elif work_type == "issue":
            resource_uri = f"devrev://issues/{normalized_id}/timeline"
        else:
            # Fallback - try ticket first, then issue
            resource_uri = f"devrev://tickets/{normalized_id}/timeline"
        
        try:
            # Use the utility function to handle resource reading consistently
            timeline_data = await read_resource_content(
                ctx, 
                resource_uri, 
                parse_json=True, 
                require_content=False
            )
            
            if not timeline_data:
                return f"No timeline entries found for {work_type} {display_id}"
                
        except Exception as resource_error:
            await ctx.error(f"Error reading resource {resource_uri}: {str(resource_error)}")
            # If JSON parsing failed but we got content, try fallback with raw content
            try:
                timeline_data = await read_resource_content(
                    ctx, 
                    resource_uri, 
                    parse_json=False, 
                    require_content=False
                )
                if format == "full" and timeline_data:
                    return str(timeline_data)
                else:
                    return f"Error: Could not parse timeline data for {work_type} {display_id}"
            except Exception:
                raise resource_error
        
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
            return _format_summary(timeline_data, normalized_id, display_id, work_type)
        elif format == "detailed":
            return _format_detailed(timeline_data, normalized_id, display_id, work_type)
        else:  # format == "full"
            try:
                return json.dumps(timeline_data, indent=2, default=str)
            except (TypeError, ValueError) as e:
                await ctx.error(f"Could not serialize timeline data to JSON: {str(e)}")
                return str(timeline_data)
            
    except Exception as e:
        await ctx.error(f"Failed to get timeline entries for {id}: {str(e)}")
        return f"Failed to get timeline entries for work item {id}: {str(e)}"


def _normalize_work_id(id: str) -> tuple[str, str, str]:
    """
    Normalize various work ID formats and determine the work type.
    
    Returns: (work_type, numeric_id, display_id)
    
    Accepts:
    - TKT-12345 -> ("ticket", "12345", "TKT-12345")
    - ISS-9031 -> ("issue", "9031", "ISS-9031")
    - don:core:dvrv-us-1:devo/118WAPdKBc:ticket/12345 -> ("ticket", "12345", "TKT-12345")
    - don:core:dvrv-us-1:devo/118WAPdKBc:issue/9031 -> ("issue", "9031", "ISS-9031")
    - 12345 -> ("unknown", "12345", "12345")
    """
    id_upper = id.upper()
    
    if id.startswith("don:core:"):
        if ":ticket/" in id:
            numeric_id = id.split(":ticket/")[1]
            return ("ticket", numeric_id, f"TKT-{numeric_id}")
        elif ":issue/" in id:
            numeric_id = id.split(":issue/")[1]
            return ("issue", numeric_id, f"ISS-{numeric_id}")
    elif id_upper.startswith("TKT-"):
        numeric_id = id[4:]  # Remove TKT- prefix
        return ("ticket", numeric_id, id.upper())
    elif id_upper.startswith("ISS-"):
        numeric_id = id[4:]  # Remove ISS- prefix
        return ("issue", numeric_id, id.upper())
    else:
        # Assume it's just a numeric ID - we can't determine the type
        return ("unknown", id, id)


def _format_summary(timeline_data, numeric_id: str, display_id: str, work_type: str) -> str:
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
        f"**{display_id} Timeline Summary:**",
        "",
        f"**Subject:** {summary.get('subject', 'Unknown')}",
        f"**Status:** {summary.get('current_stage', 'Unknown')}",
        f"**Customer:** {summary.get('customer', 'Unknown')}",
        f"**Created:** {summary.get('created_date', 'Unknown')}",
    ]
    
    # Add message counts with visibility breakdown
    customer_messages = [msg for msg in conversation if msg.get("speaker", {}).get("type") == "customer"]
    support_messages = [msg for msg in conversation if msg.get("speaker", {}).get("type") == "support"]
    
    lines.extend([
        "",
        (f"**Activity:** {len(customer_messages)} customer messages, "
         f"{len(support_messages)} support responses"),
    ])
    
    # Add visibility summary if available
    if isinstance(timeline_data, dict) and "visibility_summary" in timeline_data:
        vis_summary = timeline_data["visibility_summary"]
        lines.extend([
            "",
            "**Visibility Summary:**",
            (f"- Customer-visible entries: {vis_summary.get('customer_visible_entries', 0)} "
             f"({vis_summary.get('customer_visible_percentage', 0)}%)"),
            (f"- Internal-only entries: {vis_summary.get('internal_only_entries', 0)} "
             f"({vis_summary.get('internal_only_percentage', 0)}%)"),
        ])
        
        # Show breakdown by visibility level
        breakdown = vis_summary.get("visibility_breakdown", {})
        if breakdown:
            lines.append("- Visibility levels:")
            for level, count in breakdown.items():
                description = VisibilityInfo.from_visibility(level).description
                lines.append(f"  • {level}: {count} entries ({description})")
    
    # Add last activity timestamps
    if summary.get("last_customer_message"):
        lines.append(f"**Last customer message:** {summary['last_customer_message']}")
    if summary.get("last_support_response"):
        lines.append(f"**Last support response:** {summary['last_support_response']}")
    
    # Add latest messages preview with visibility indicators
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
            message_preview = (msg.get("message", "")[:100] + 
                             ("..." if len(msg.get("message", "")) > 100 else ""))
            
            # Add visibility indicator
            visibility_info = msg.get("visibility_info", {})
            visibility_indicator = ""
            if visibility_info:
                level = visibility_info.get("level", "external")
                if level == "private":
                    visibility_indicator = "🔒 "
                elif level == "internal":
                    visibility_indicator = "🏢 "
                elif level == "external":
                    visibility_indicator = "👥 "
                elif level == "public":
                    visibility_indicator = "🌐 "
            
            lines.append(
                f"- **{speaker.get('name', 'Unknown')}** ({timestamp}): "
                f"{visibility_indicator}{message_preview}"
            )
    
    # Add artifacts info
    if isinstance(timeline_data, dict):
        artifacts = timeline_data.get("all_artifacts", [])
        if artifacts:
            lines.extend([
                "",
                f"**Attachments:** {len(artifacts)} file(s) attached"
            ])
    
    return "\n".join(lines)


def _format_detailed(timeline_data, numeric_id: str, display_id: str, work_type: str) -> str:
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
        f"**{display_id} Detailed Timeline:**",
        "",
        f"**Subject:** {summary.get('subject', 'Unknown')}",
        f"**Status:** {summary.get('current_stage', 'Unknown')}",
        f"**Customer:** {summary.get('customer', 'Unknown')}",
        "",
        "**Conversation Thread:**"
    ]
    
    # Add each conversation entry with visibility information
    for msg in conversation:
        speaker = msg.get("speaker", {})
        timestamp = msg.get("timestamp", "")
        message = msg.get("message", "")
        artifacts = msg.get("artifacts", [])
        visibility_info = msg.get("visibility_info", {})
        
        # Format timestamp to be more readable
        display_time = timestamp[:19].replace("T", " ") if timestamp else "Unknown time"
        
        # Format visibility info
        visibility_text = ""
        if visibility_info:
            level = visibility_info.get("level", "external")
            description = visibility_info.get("description", "")
            audience = visibility_info.get("audience", "")
            
            # Add visibility indicator
            if level == "private":
                visibility_text = " 🔒 [PRIVATE - Creator only]"
            elif level == "internal":
                visibility_text = " 🏢 [INTERNAL - Dev org only]"
            elif level == "external":
                visibility_text = " 👥 [EXTERNAL - Dev org + customers]"
            elif level == "public":
                visibility_text = " 🌐 [PUBLIC - Everyone]"
        
        lines.extend([
            "",
            (f"**{msg.get('seq', '?')}. {speaker.get('name', 'Unknown')} "
             f"({speaker.get('type', 'unknown')}) - {display_time}**{visibility_text}")
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
        
        # Add visibility details if relevant
        if visibility_info and visibility_info.get("level") in ["private", "internal"]:
            lines.append(f"   *Visibility: {visibility_info.get('description', 'Unknown')}*")
    
    # Add key events summary with visibility
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
                
                # Add visibility indicator for events
                visibility_info = event.get("visibility_info", {})
                visibility_indicator = ""
                if visibility_info:
                    level = visibility_info.get("level", "external")
                    if level == "private":
                        visibility_indicator = " 🔒"
                    elif level == "internal":
                        visibility_indicator = " 🏢"
                    elif level == "external":
                        visibility_indicator = " 👥"
                    elif level == "public":
                        visibility_indicator = " 🌐"
                
                lines.append(f"- {event_time}: {event_type} by {actor}{visibility_indicator}")
        
        # Add overall visibility summary
        if "visibility_summary" in timeline_data:
            vis_summary = timeline_data["visibility_summary"]
            lines.extend([
                "",
                "**Visibility Overview:**",
                f"- Total entries: {vis_summary.get('total_entries', 0)}",
                (f"- Customer-visible: {vis_summary.get('customer_visible_entries', 0)} "
                 f"({vis_summary.get('customer_visible_percentage', 0)}%)"),
                (f"- Internal-only: {vis_summary.get('internal_only_entries', 0)} "
                 f"({vis_summary.get('internal_only_percentage', 0)}%)")
            ])
    
    return "\n".join(lines)