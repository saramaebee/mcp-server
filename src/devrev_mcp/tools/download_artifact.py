"""
DevRev Download Artifact Tool

Provides functionality to download DevRev artifacts to a specified directory.
"""

import json
import os
import requests
from pathlib import Path
from fastmcp import Context
from ..utils import read_resource_content
from ..error_handler import tool_error_handler


@tool_error_handler("download_artifact")
async def download_artifact(artifact_id: str, download_directory: str, ctx: Context) -> str:
    """
    Download a DevRev artifact to a specified directory.
    
    Args:
        artifact_id: The DevRev artifact ID
        download_directory: The directory path where the artifact should be downloaded
        ctx: FastMCP context
    
    Returns:
        JSON string containing download result information
    """
    try:
        await ctx.info(f"Starting download of artifact {artifact_id} to {download_directory}")
        
        # Ensure download directory exists
        os.makedirs(download_directory, exist_ok=True)
        
        # Get artifact information using the artifact resource
        resource_uri = f"devrev://artifacts/{artifact_id}"
        artifact_data = await read_resource_content(ctx, resource_uri, parse_json=True)
        artifact_info = artifact_data.get("artifact", {})
        
        await ctx.info(f"Retrieved artifact metadata: {artifact_info.get('display_id', artifact_id)}")
        
        # Check if download URL is available in the artifact data
        download_url = None
        file_info = artifact_info.get("file", {})
        
        # Look for download URL in various possible locations (artifact resource already tried locate endpoint)
        if "download_url" in file_info:
            download_url = file_info["download_url"]
        elif "url" in file_info:
            download_url = file_info["url"]
        elif "download_url" in artifact_info:
            download_url = artifact_info["download_url"]
        elif "url" in artifact_info:
            download_url = artifact_info["url"]
        
        if not download_url:
            error_msg = "No download URL found for artifact. The artifact may not be downloadable or the API doesn't provide direct download URLs."
            await ctx.error(error_msg)
            return json.dumps({
                "success": False,
                "error": error_msg,
                "artifact_id": artifact_id,
                "artifact_info": artifact_info
            }, indent=2)
        
        # Extract filename from artifact info or URL, prioritizing the actual filename
        filename = file_info.get("name") or file_info.get("filename")
        if not filename:
            # Extract from URL as fallback
            from urllib.parse import urlparse
            parsed_url = urlparse(download_url)
            filename = os.path.basename(parsed_url.path)
        if not filename:
            # Use display_id as fallback
            filename = artifact_info.get("display_id")
        if not filename:
            filename = f"artifact_{artifact_id}"
        
        # Download the file
        download_path = Path(download_directory) / filename
        
        await ctx.info(f"Downloading artifact from {download_url} to {download_path}")
        
        # Download with streaming to handle large files
        with requests.get(download_url, stream=True, timeout=60) as response:
            response.raise_for_status()
            
            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        file_size = os.path.getsize(download_path)
        
        result = {
            "success": True,
            "artifact_id": artifact_id,
            "filename": filename,
            "download_path": str(download_path),
            "file_size": file_size,
            "download_directory": download_directory,
            "artifact_info": {
                "display_id": artifact_info.get("display_id"),
                "type": file_info.get("type"),
                "mime_type": file_info.get("mime_type"),
                "created_date": artifact_info.get("created_date")
            }
        }
        
        await ctx.info(f"Successfully downloaded artifact {artifact_id} ({file_size} bytes) to {download_path}")
        return json.dumps(result, indent=2)
        
    except requests.RequestException as e:
        error_msg = f"Failed to download artifact {artifact_id}: {str(e)}"
        await ctx.error(error_msg)
        return json.dumps({
            "success": False,
            "error": error_msg,
            "artifact_id": artifact_id
        }, indent=2)
        
    except Exception as e:
        error_msg = f"Failed to download artifact {artifact_id}: {str(e)}"
        await ctx.error(error_msg)
        return json.dumps({
            "success": False,
            "error": error_msg,
            "artifact_id": artifact_id
        }, indent=2)