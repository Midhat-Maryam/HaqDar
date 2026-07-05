"""
Node 5: Authority Router
Matches the classified issue type to the correct forum/authority and filing process.
Calls the lookup_authority function directly (MCP-wrapped version lives in mcp_server/).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import requests
from config import DATASET_PATH, DEFAULT_CITY
from agents.state import HaqDarState

with open(DATASET_PATH, "r", encoding="utf-8") as f:
    _dataset = json.load(f)

_ROUTING = _dataset["authority_routing"]


_FORUM_SEARCH_QUERY = {
    "pricing_receipt_disclosure": "Supply and Prices Department Sindh",
    "defective_product": "District Consumer Court",
    "defective_service": "District Consumer Court",
    "unfair_deceptive_practice": "Sindh Consumer Protection Council Authority",
}


def lookup_authority(issue_type: str) -> dict:
    """
    Core lookup function. Wrapped as an MCP tool in mcp_server/server.py
    so it can be called either directly (as here) or via MCP protocol.
    """
    if issue_type not in _ROUTING:
        return {
            "forum": "Consumer Protection Council (general inquiry)",
            "process": "Issue type unclear — contact the Provincial Consumer Protection Council or nearest District Council for guidance before filing.",
            "pre_requisite": "None",
        }
    return _ROUTING[issue_type]


def find_forum_location(issue_type: str, city: str = DEFAULT_CITY) -> dict:
    """
    Resolves an issue type to a real, searchable forum location using
    OpenStreetMap's free Nominatim API (no API key or billing required).
    Wrapped as an MCP tool (locate_forum_tool) in mcp_server/server.py so it
    can also be called directly via MCP protocol.

    Note: takes issue_type (not the raw "forum" description string from the
    dataset) because that description isn't a real place name a geocoder
    could ever match — see _FORUM_SEARCH_QUERY above.

    Returns {"found": False, "reason": ...} if nothing is found — callers
    should handle this gracefully rather than assume a hit.
    """
    search_term = _FORUM_SEARCH_QUERY.get(issue_type, "District Consumer Court")
    query = f"{search_term}, {city}, Sindh, Pakistan"

    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": query, "format": "json", "limit": 1, "addressdetails": 1}
    headers = {"User-Agent": "HaqDar-ConsumerRightsApp/1.0 (student capstone project)"}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        resp.raise_for_status()
        results = resp.json()
    except Exception as e:
        return {"found": False, "reason": str(e)}

    if not results:
        return {"found": False, "reason": f"no matching location found for '{search_term}' in {city}"}

    place = results[0]
    lat, lng = place.get("lat"), place.get("lon")

    return {
        "found": True,
        "name": place.get("display_name", search_term).split(",")[0],
        "address": place.get("display_name"),
        "phone": None,  # Nominatim doesn't provide phone/contact data
        "lat": float(lat) if lat else None,
        "lng": float(lng) if lng else None,
        "maps_link": (
            f"https://www.openstreetmap.org/?mlat={lat}&mlon={lng}#map=17/{lat}/{lng}"
            if lat and lng else None
        ),
    }


def route_to_authority(state: HaqDarState) -> HaqDarState:
    issue_type = state.get("issue_type", "unclear")
    info = lookup_authority(issue_type)

    
    location = find_forum_location(issue_type)
    info = {**info, "location": location}

    return {
        **state,
        "authority_info": info,
    }
