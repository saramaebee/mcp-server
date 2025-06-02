"""
Copyright (c) 2025 DevRev, Inc.
SPDX-License-Identifier: MIT

This module provides utility functions for making authenticated requests to the DevRev API.
"""

import os
import requests
from typing import Any, Dict

def make_devrev_request(endpoint: str, payload: Dict[str, Any]) -> requests.Response:
    """
    Make an authenticated request to the DevRev API.
    
    Args:
        endpoint: The API endpoint path (use constants from endpoints.py)
        payload: The JSON payload to send
    
    Returns:
        requests.Response object
    
    Raises:
        ValueError: If DEVREV_API_KEY environment variable is not set
        requests.RequestException: If the HTTP request fails
    """
    api_key = os.environ.get("DEVREV_API_KEY")
    if not api_key:
        raise ValueError("DEVREV_API_KEY environment variable is not set")

    headers = {
        "Authorization": f"{api_key}",
        "Content-Type": "application/json",
    }
    
    try:
        response = requests.post(
            f"https://api.devrev.ai/{endpoint}",
            headers=headers,
            json=payload,
            timeout=30  # Add timeout for better error handling
        )
        return response
    except requests.RequestException as e:
        raise requests.RequestException(f"DevRev API request failed for endpoint '{endpoint}': {e}") from e


def normalize_ticket_id(ticket_id: str) -> str:
    """
    Normalize ticket ID to TKT-XXXXX format for API calls.
    
    Args:
        ticket_id: The input ticket ID (e.g., "12345", "TKT-12345", "tkt-12345")
    
    Returns:
        Normalized ticket ID in TKT-XXXXX format
    
    Examples:
        normalize_ticket_id("12345") -> "TKT-12345"
        normalize_ticket_id("TKT-12345") -> "TKT-12345"
        normalize_ticket_id("tkt-12345") -> "TKT-12345"
    """
    if not ticket_id:
        return ticket_id
    
    # Remove any existing TKT- prefix (case insensitive)
    if ticket_id.upper().startswith("TKT-"):
        numeric_id = ticket_id[4:]  # Remove TKT- or tkt-
    else:
        numeric_id = ticket_id
    
    # Return normalized format
    return f"TKT-{numeric_id}"


def extract_ticket_id_from_object(object_id: str) -> str:
    """
    Extract numeric ticket ID from object ID containing TKT- prefix.
    
    Args:
        object_id: Object ID that may contain TKT- prefix
    
    Returns:
        Numeric part of ticket ID
    
    Examples:
        extract_ticket_id_from_object("TKT-12345") -> "12345"
        extract_ticket_id_from_object("12345") -> "12345"
    """
    if not object_id:
        return object_id
    
    if "TKT-" in object_id:
        return object_id.replace("TKT-", "")
    
    return object_id
