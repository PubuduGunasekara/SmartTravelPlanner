"""
Travel Time Matrix

Builds a travel time matrix between all activity locations using:
- Nominatim for geocoding (addresses -> coordinates)
- OSRM public server for routing (coordinates -> travel times)

Caches coordinates so only new addresses need geocoding.

Usage:
    from travel_matrix import ensure_matrix, get_travel_time, load_matrix

    # Build/update matrix — only geocodes new addresses
    ensure_matrix("activities.json", "travel_matrix.json", extra_addresses=["123 Hotel St"])

    # Load and use
    matrix, locations = load_matrix("travel_matrix.json")
    minutes = get_travel_time(matrix, locations, "123 Hotel St", "1000 5th Ave")
"""

import json
import time
import os
import requests
from config import *

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def load_locations(json_path: str, extra_addresses: list[str] = None) -> list[str]:
    with open(json_path) as f:
        data = json.load(f)
    activities = data if isinstance(data, list) else data.get("activities", [])
    addresses = set()
    for a in activities:
        if a.get("start_location"):
            addresses.add(a["start_location"])
        if a.get("end_location"):
            addresses.add(a["end_location"])
    if extra_addresses:
        for addr in extra_addresses:
            addresses.add(addr)
    return sorted(addresses)


def geocode(address: str, retries: int = 3) -> tuple[float, float] | None:
    for attempt in range(retries):
        try:
            resp = requests.get(NOMINATIM_URL, params={
                "q": address,
                "format": "json",
                "limit": 1,
            }, headers={
                "User-Agent": "TravelPlannerDev/1.0"
            }, timeout=10)
            results = resp.json()
            if results:
                return (float(results[0]["lat"]), float(results[0]["lon"]))
            return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                print(f"  Failed to geocode: {address} ({e})")
                return None


def fetch_osrm_table(coords: list[tuple[float, float]], profile: str = "car", retries: int = 3) -> list[list[float]] | None:
    url = f"https://router.project-osrm.org/table/v1/{profile}/"
    coord_str = ";".join(f"{lng},{lat}" for lat, lng in coords)
    url += coord_str
    for attempt in range(retries):
        try:
            resp = requests.get(url, params={"annotations": "duration"}, timeout=60)
            data = resp.json()
            if data.get("code") != "Ok":
                print(f"  OSRM error: {data.get('code')} - {data.get('message', '')}")
                return None
            return data["durations"]
        except Exception as e:
            if attempt < retries - 1:
                wait = 5 * (attempt + 1)
                print(f"  OSRM request failed ({e}), retrying in {wait}s... ({attempt + 1}/{retries})")
                time.sleep(wait)
            else:
                print(f"  OSRM request failed after {retries} attempts: {e}")
                return None


def ensure_matrix(
    json_path: str,
    save_path: str,
    extra_addresses: list[str] = None,
    profile: str = "car",
) -> tuple[list[list[float]], list[str]]:
    """
    Build or update a travel time matrix. Only geocodes new addresses.
    Rebuilds the OSRM matrix if any new coordinates were added.

    Args:
        json_path:       Path to the activities JSON.
        save_path:        Path to save/load the cached matrix JSON.
        extra_addresses:  Additional addresses (hotels, start/end points).
        profile:          OSRM routing profile.

    Returns:
        (matrix, locations)
    """
    # Load existing cache if available
    cached_coords = {}
    if os.path.exists(save_path):
        with open(save_path) as f:
            cached = json.load(f)
        cached_coords = cached.get("coordinates", {})

    # Get all addresses needed
    all_addresses = load_locations(json_path, extra_addresses)
    print(f"Total addresses needed: {len(all_addresses)}")

    # Find which ones need geocoding
    new_addresses = [a for a in all_addresses if a not in cached_coords]

    if new_addresses:
        print(f"Geocoding {len(new_addresses)} new addresses...")
        for i, addr in enumerate(new_addresses):
            print(f"  [{i+1}/{len(new_addresses)}]: {addr[:60]}...")
            result = geocode(addr)
            if result:
                cached_coords[addr] = result
            else:
                print(f"  WARNING: Could not geocode '{addr}', skipping.")
            time.sleep(1.1)
        needs_rebuild = True
    else:
        print("All addresses already geocoded.")
        if os.path.exists(save_path):
            with open(save_path) as f:
                cached = json.load(f)
            cached_locations = set(cached.get("locations", []))
            needed = set(a for a in all_addresses if a in cached_coords)
            needs_rebuild = needed != cached_locations
        else:
            needs_rebuild = True

    # Filter to successfully geocoded addresses
    valid_addresses = [a for a in all_addresses if a in cached_coords]
    valid_coords = [cached_coords[a] for a in valid_addresses]

    if len(valid_addresses) < 2:
        raise ValueError(f"Only {len(valid_addresses)} addresses geocoded. Need at least 2.")

    if needs_rebuild:
        print(f"Fetching OSRM matrix ({len(valid_addresses)}x{len(valid_addresses)})...")
        raw_matrix = fetch_osrm_table(valid_coords, profile)
        if raw_matrix is None:
            raise RuntimeError("Failed to fetch OSRM matrix.")
        matrix = [
            [round(cell / 60, 1) if cell is not None else None for cell in row]
            for row in raw_matrix
        ]
    else:
        print("Matrix is up to date.")
        matrix = cached["matrix"]

    # Save everything
    with open(save_path, "w") as f:
        json.dump({
            "locations": valid_addresses,
            "coordinates": cached_coords,
            "matrix": matrix,
        }, f, indent=2)

    print("Done.")
    return matrix, valid_addresses


def get_travel_time(
    matrix: list[list[float]],
    locations: list[str],
    from_addr: str,
    to_addr: str,
) -> float | None:
    if from_addr == to_addr:
        return 0
    try:
        i = locations.index(from_addr)
        j = locations.index(to_addr)
        if matrix[i][j] is None:
            return None
        return matrix[i][j] + TRAVEL_BUFFER
    except ValueError:
        return None


def load_matrix(path: str) -> tuple[list[list[float]], list[str]]:
    with open(path) as f:
        data = json.load(f)
    return data["matrix"], data["locations"]


