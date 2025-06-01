"""
DevRev Artifact Resource Handler

Provides specialized resource access for DevRev artifacts with metadata and download URLs.
"""

import json
from fastmcp import Context
from ..utils import make_devrev_request


async def artifact(artifact_id: str, ctx: Context, devrev_cache: dict) -> str:
    """
    Access DevRev artifact metadata.
    
    Args:
        artifact_id: The DevRev artifact ID
        ctx: FastMCP context
        devrev_cache: Cache dictionary for storing results
    
    Returns:
        JSON string containing the artifact metadata
    """
    try:
        cache_key = f"artifact:{artifact_id}"
        
        # Check cache first
        if cache_key in devrev_cache:
            await ctx.info(f"Retrieved artifact {artifact_id} from cache")
            return devrev_cache[cache_key]
        
        await ctx.info(f"Fetching artifact {artifact_id} from DevRev API")
        
        # For artifacts, use artifacts.get endpoint
        response = make_devrev_request(
            "artifacts.get",
            {"id": artifact_id}
        )
        
        if response.status_code != 200:
            error_text = response.text
            await ctx.error(f"Failed to fetch artifact {artifact_id}: HTTP {response.status_code} - {error_text}")
            raise ValueError(f"Failed to fetch artifact {artifact_id} (HTTP {response.status_code}): {error_text}")
        
        result = response.json()
        
        # Try to get download URL if available through artifacts.locate
        artifact_info = result.get("artifact", {})
        if artifact_info and not any(key in artifact_info.get("file", {}) for key in ["download_url", "url"]):
            try:
                await ctx.info(f"Attempting to get download URL for artifact {artifact_id}")
                locate_response = make_devrev_request(
                    "artifacts.locate",
                    {"id": artifact_id}
                )
                
                if locate_response.status_code == 200:
                    locate_data = locate_response.json()
                    locate_artifact = locate_data.get("artifact", {})
                    if locate_artifact:
                        # Merge locate data into the main artifact data
                        if "download_url" in locate_artifact:
                            artifact_info["download_url"] = locate_artifact["download_url"]
                        if "file" in locate_artifact and "download_url" in locate_artifact["file"]:
                            if "file" not in artifact_info:
                                artifact_info["file"] = {}
                            artifact_info["file"]["download_url"] = locate_artifact["file"]["download_url"]
                        await ctx.info(f"Successfully added download URL for artifact {artifact_id}")
                else:
                    await ctx.info(f"artifacts.locate not available for {artifact_id}: HTTP {locate_response.status_code}")
            except Exception as locate_error:
                await ctx.info(f"Could not locate download URL for artifact {artifact_id}: {str(locate_error)}")
                # Continue without download URL
        
        # Add navigation links to timeline entry (artifacts belong to timeline entries)
        # Note: We'd need to determine the timeline entry ID from the artifact context
        # For now, adding a placeholder structure that could be populated based on API response
        result["links"] = {
            "timeline_entry": "devrev://timeline-entries/{timeline_entry_id}",  # Would need actual ID
            "note": "Artifact belongs to a specific timeline entry, which belongs to a ticket"
        }
        
        # Cache the result
        devrev_cache[cache_key] = json.dumps(result, indent=2)
        await ctx.info(f"Successfully retrieved and cached artifact: {artifact_id}")
        
        return devrev_cache[cache_key]
        
    except Exception as e:
        await ctx.error(f"Failed to get artifact resource {artifact_id}: {str(e)}")
        raise ValueError(f"Artifact resource {artifact_id} not found: {str(e)}")