"""Google Maps Platform services for TalentScout AI.

Provides geocoding and nearby place search using the Geocoding API and Places API (New).
API key is read securely from the environment variable GOOGLE_MAPS_API_KEY.
"""

import json
import os
import urllib.parse
import urllib.request
from typing import Any


def _get_api_key() -> str:
    """Retrieve Google Maps API key from environment."""
    key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if not key:
        raise ValueError("GOOGLE_MAPS_API_KEY environment variable is not set.")
    return key


def geocode_address(address: str) -> dict[str, Any]:
    """Turn a street address, city, or venue into geographic coordinates.

    Args:
        address: The address or location to geocode (e.g. '1600 Amphitheatre Parkway, Mountain View, CA' or 'San Francisco, CA').

    Returns:
        A dictionary containing key fields: name, formatted address, and location (latitude/longitude coordinates).
    """
    try:
        api_key = _get_api_key()
    except ValueError as e:
        return {"error": str(e)}

    params = urllib.parse.urlencode({
        "address": address,
        "key": api_key,
    })
    url = f"https://maps.googleapis.com/maps/api/geocode/json?{params}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TalentScout-AI/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        status = data.get("status")
        if status != "OK" or not data.get("results"):
            return {
                "error": f"Geocoding failed with status: {status}",
                "address": address,
            }

        first_result = data["results"][0]
        geom = first_result.get("geometry", {}).get("location", {})
        formatted_address = first_result.get("formatted_address", address)

        return {
            "name": address,
            "address": formatted_address,
            "location": {
                "latitude": geom.get("lat"),
                "longitude": geom.get("lng"),
            },
        }
    except Exception as e:
        return {"error": f"Error calling Geocoding API: {str(e)}"}


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "cafe",
    radius_meters: float = 1500.0,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """Find nearby places of a given type around coordinates using Places API (New).

    Args:
        latitude: Latitude coordinate for search center.
        longitude: Longitude coordinate for search center.
        place_type: Type of place to search for (e.g. 'cafe', 'restaurant', 'coworking_space', 'library', 'lodging').
        radius_meters: Radius in meters around the center point (default 1500m).
        max_results: Maximum number of places to return (default 5, up to 20).

    Returns:
        A list of nearby places, each containing key fields: name, address, and location.
    """
    try:
        api_key = _get_api_key()
    except ValueError as e:
        return [{"error": str(e)}]

    endpoint = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location",
        "User-Agent": "TalentScout-AI/1.0",
    }

    body = json.dumps({
        "includedTypes": [place_type],
        "maxResultCount": min(max(1, max_results), 20),
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "radius": float(radius_meters),
            }
        },
    }).encode("utf-8")

    try:
        req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

        places = data.get("places", [])
        results = []
        for p in places:
            results.append({
                "name": p.get("displayName", {}).get("text", "Unknown"),
                "address": p.get("formattedAddress", ""),
                "location": {
                    "latitude": p.get("location", {}).get("latitude"),
                    "longitude": p.get("location", {}).get("longitude"),
                },
            })
        return results
    except Exception as e:
        return [{"error": f"Error calling Places API (New): {str(e)}"}]
