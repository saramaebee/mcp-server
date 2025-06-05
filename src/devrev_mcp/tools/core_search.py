"""
Copyright (c) 2025 DevRev, Inc.
SPDX-License-Identifier: MIT

This module provides core search functionality for DevRev objects.
"""

import json
from typing import Dict, Any, List, Optional
from fastmcp import Context

from ..utils import make_devrev_request
from ..error_handler import tool_error_handler
from ..endpoints import SEARCH_CORE


@tool_error_handler("core_search")
async def core_search(
    ctx: Context,
    query: Optional[str] = None,
    title: Optional[str] = None,
    tag: Optional[str] = None,
    type: Optional[str] = None,
    status: Optional[str] = None,
    namespace: Optional[str] = None
) -> str:
    """
    Search DevRev using core search with structured parameters.
    
    Args:
        ctx: FastMCP context for logging
        query: Free text search query
        title: Search by title/summary text
        tag: Search by tag
        type: Filter by object type (ticket, issue, article, etc.)
        status: Filter by status
        namespace: The namespace to search in (article, issue, ticket, part, dev_user)
    
    Returns:
        JSON string containing parsed search results with key information
    """
    # Build search parameters
    search_params = {}
    
    if query:
        search_params["query"] = query
    if title:
        search_params["title"] = title
    if tag:
        search_params["tag"] = tag
    if type:
        search_params["type"] = type
    if status:
        search_params["status"] = status
    if namespace:
        search_params["namespace"] = namespace
    
    # Ensure we have at least one search parameter
    if not search_params:
        raise ValueError("At least one search parameter must be provided")
    
    try:
        # Log the search parameters for debugging
        param_summary = ", ".join([f"{k}={v}" for k, v in search_params.items()])
        await ctx.info(f"Core search with parameters: {param_summary}")
        
        response = make_devrev_request(SEARCH_CORE, search_params)
        
        if response.status_code != 200:
            error_text = response.text
            await ctx.error(f"Core search failed with status {response.status_code}: {error_text}")
            raise ValueError(f"Core search failed with status {response.status_code}: {error_text}")
        
        search_results = response.json()
        parsed_results = _parse_core_search_results(search_results, search_params)
        
        await ctx.info(f"Core search completed successfully with {len(parsed_results.get('results', []))} results")
        
        return json.dumps(parsed_results, indent=2)
    
    except Exception as e:
        await ctx.error(f"Core search operation failed: {str(e)}")
        raise


def _parse_core_search_results(raw_results: Dict[str, Any], search_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse raw core search results to extract useful information.
    
    Args:
        raw_results: Raw search results from DevRev API
        search_params: The search parameters that were used
        
    Returns:
        Parsed results with key information extracted
    """
    parsed = {
        "search_info": {
            "search_type": "core",
            "parameters": search_params,
            "total_results": len(raw_results.get("results", []))
        },
        "results": []
    }
    
    for result in raw_results.get("results", []):
        if result.get("type") == "work" and "work" in result:
            work = result["work"]
            parsed_result = _parse_work_result(work)
            parsed["results"].append(parsed_result)
        elif result.get("type") == "article" and "article" in result:
            article = result["article"]
            parsed_result = _parse_article_result(article)
            parsed["results"].append(parsed_result)
        elif result.get("type") == "part" and "part" in result:
            part = result["part"]
            parsed_result = _parse_part_result(part)
            parsed["results"].append(parsed_result)
        elif result.get("type") == "dev_user" and "dev_user" in result:
            dev_user = result["dev_user"]
            parsed_result = _parse_dev_user_result(dev_user)
            parsed["results"].append(parsed_result)
        else:
            # For other types, include basic info
            parsed_result = {
                "type": result.get("type", "unknown"),
                "id": result.get("id"),
                "snippet": result.get("snippet", "")
            }
            parsed["results"].append(parsed_result)
    
    return parsed


def _parse_work_result(work: Dict[str, Any]) -> Dict[str, Any]:
    """Parse work (ticket/issue) search result."""
    return {
        "type": "work",
        "work_type": work.get("type"),
        "id": work.get("id"),
        "display_id": work.get("display_id"),
        "title": work.get("title"),
        "severity": work.get("severity"),
        "priority": work.get("priority"),
        "stage": work.get("stage", {}).get("name"),
        "status": work.get("stage", {}).get("name"),  # DevRev uses stage as status
        "owned_by": [
            {
                "name": owner.get("display_name"),
                "email": owner.get("email"),
                "id": owner.get("id")
            }
            for owner in work.get("owned_by", [])
        ],
        "rev_org": {
            "name": work.get("rev_org", {}).get("display_name"),
            "id": work.get("rev_org", {}).get("id")
        },
        "tags": [tag.get("name") for tag in work.get("tags", [])],
        "links": _generate_work_links(work)
    }


def _parse_article_result(article: Dict[str, Any]) -> Dict[str, Any]:
    """Parse article search result."""
    return {
        "type": "article",
        "id": article.get("id"),
        "display_id": article.get("display_id"),
        "title": article.get("title"),
        "status": article.get("status"),
        "authored_by": {
            "name": article.get("authored_by", {}).get("display_name"),
            "email": article.get("authored_by", {}).get("email"),
            "id": article.get("authored_by", {}).get("id")
        },
        "tags": [tag.get("name") for tag in article.get("tags", [])]
    }


def _parse_part_result(part: Dict[str, Any]) -> Dict[str, Any]:
    """Parse part search result."""
    return {
        "type": "part",
        "id": part.get("id"),
        "display_id": part.get("display_id"),
        "name": part.get("name"),
        "description": part.get("description"),
        "tags": [tag.get("name") for tag in part.get("tags", [])]
    }


def _parse_dev_user_result(dev_user: Dict[str, Any]) -> Dict[str, Any]:
    """Parse dev_user search result."""
    return {
        "type": "dev_user",
        "id": dev_user.get("id"),
        "display_id": dev_user.get("display_id"),
        "display_name": dev_user.get("display_name"),
        "email": dev_user.get("email"),
        "state": dev_user.get("state")
    }


def _generate_work_links(work: Dict[str, Any]) -> Dict[str, str]:
    """Generate navigation links for work items."""
    links = {}
    
    display_id = work.get("display_id", "")
    work_type = work.get("type", "")
    
    if display_id:
        links["work_item"] = f"devrev://works/{display_id}"
        
        if work_type == "ticket" and display_id.startswith("TKT-"):
            ticket_num = display_id.replace("TKT-", "")
            links.update({
                "ticket": f"devrev://tickets/{ticket_num}",
                "timeline": f"devrev://tickets/{ticket_num}/timeline",
                "artifacts": f"devrev://tickets/{ticket_num}/artifacts"
            })
        elif work_type == "issue" and display_id.startswith("ISS-"):
            issue_num = display_id.replace("ISS-", "")
            links.update({
                "issue": f"devrev://issues/{issue_num}",
                "timeline": f"devrev://issues/{issue_num}/timeline",
                "artifacts": f"devrev://issues/{issue_num}/artifacts"
            })
    
    return links