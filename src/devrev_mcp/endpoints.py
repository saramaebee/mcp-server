"""
DevRev API Endpoints Constants

This module defines all DevRev API endpoint strings used throughout the application.
Centralizing these constants prevents typos and makes API changes easier to manage.
"""


class DevRevEndpoints:
    """DevRev API endpoint constants for consistent usage across the application."""
    
    # Works (Tickets, Issues, etc.)
    WORKS_GET = "works.get"
    WORKS_CREATE = "works.create"
    WORKS_UPDATE = "works.update"
    
    # Timeline Entries
    TIMELINE_ENTRIES_LIST = "timeline-entries.list"
    TIMELINE_ENTRIES_GET = "timeline-entries.get"
    
    # Artifacts
    ARTIFACTS_GET = "artifacts.get"
    ARTIFACTS_LOCATE = "artifacts.locate"
    
    # Search
    SEARCH_HYBRID = "search.hybrid"


# Convenience exports for simpler imports
WORKS_GET = DevRevEndpoints.WORKS_GET
WORKS_CREATE = DevRevEndpoints.WORKS_CREATE
WORKS_UPDATE = DevRevEndpoints.WORKS_UPDATE
TIMELINE_ENTRIES_LIST = DevRevEndpoints.TIMELINE_ENTRIES_LIST
TIMELINE_ENTRIES_GET = DevRevEndpoints.TIMELINE_ENTRIES_GET
ARTIFACTS_GET = DevRevEndpoints.ARTIFACTS_GET
ARTIFACTS_LOCATE = DevRevEndpoints.ARTIFACTS_LOCATE
SEARCH_HYBRID = DevRevEndpoints.SEARCH_HYBRID