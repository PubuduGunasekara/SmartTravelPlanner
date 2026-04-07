"""
Travel Time Matrix

Builds a travel time matrix between all activity locations using:
- Nominatim for geocoding (addresses -> coordinates)
- OSRM public server for routing (coordinates -> travel times)

Usage:
    from travel_matrix import build_matrix, get_travel_time

    matrix, locations = build_matrix("activities.json", hotel_address="123 Main St, NYC")
    minutes = get_travel_time(matrix, locations, "123 Main St, NYC", "1000 5th Ave, NYC")
"""

import json
import time
import requests



NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_TABLE_URL = "https://router.project-osrm.org/table/v1/car"  # car is most reliable on public server


def load_locations(json_path: str, start_address: str = None, end_address: str = None) -> list[str]:
    """Extract all unique addresses from the activities JSON."""
    with open(json_path) as f:
        data = json.load(f)

    activities = data if isinstance(data, list) else data.get("activities", [])

    addresses = set()
    for a in activities:
        if a.get("start_location"):
            addresses.add(a["start_location"])
        if a.get("end_location"):
            addresses.add(a["end_location"])

    if start_address:
        addresses.add(start_address)
    if end_address: 
        addresses.add(end_address)

    return sorted(addresses)


def geocode(address: str, retries: int = 3) -> tuple[float, float] | None:
    """Geocode an address to (lat, lng) using Nominatim. Returns None on failure."""
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


def geocode_all(addresses: list[str]) -> dict[str, tuple[float, float]]:
    """Geocode a list of addresses. Nominatim requires 1 req/sec."""
    coords = {}
    for i, addr in enumerate(addresses):
        print(f"  Geocoding [{i+1}/{len(addresses)}]: {addr[:60]}...")
        result = geocode(addr)
        if result:
            coords[addr] = result
        else:
            print(f"  WARNING: Could not geocode '{addr}', skipping.")
        time.sleep(1.1)  # Nominatim rate limit
    return coords


def fetch_osrm_table(coords: list[tuple[float, float]], profile: str = "foot", retries: int = 3) -> list[list[float]] | None:
    """
    Call OSRM /table endpoint. Returns matrix of travel times in seconds.
    Profile can be 'foot', 'car', or 'bicycle'.
    """
    url = f"https://router.project-osrm.org/table/v1/{profile}/"

    # OSRM wants lng,lat (not lat,lng)
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


def build_matrix(
    json_path: str,
    start_address: str = None,
    end_address: str = None,
    profile: str = "car",
) -> tuple[list[list[float]], list[str]]:
    """
    Build a travel time matrix for all locations in the activities JSON.

    Args:
        json_path: Path to the activities JSON file.
        hotel_address: Optional hotel/start address to include.
        profile: OSRM routing profile ('foot', 'car', 'bicycle').

    Returns:
        (matrix, locations) where:
        - matrix[i][j] is travel time in minutes from locations[i] to locations[j]
        - locations is the ordered list of addresses
    """
    print("Loading locations...")
    addresses = load_locations(json_path, start_address, end_address)
    print(f"  Found {len(addresses)} unique locations.")

    print("Geocoding addresses...")
    coords = geocode_all(addresses)

    # Filter to only successfully geocoded addresses
    valid_addresses = [a for a in addresses if a in coords]
    valid_coords = [coords[a] for a in valid_addresses]

    if len(valid_addresses) < 2:
        raise ValueError(f"Only {len(valid_addresses)} addresses geocoded successfully. Need at least 2.")

    print(f"Fetching OSRM travel time matrix ({len(valid_addresses)}x{len(valid_addresses)})...")
    raw_matrix = fetch_osrm_table(valid_coords, profile)

    if raw_matrix is None:
        raise RuntimeError("Failed to fetch OSRM matrix.")

    # Convert seconds to minutes
    matrix = [
        [round(cell / 60, 1) if cell is not None else None for cell in row]
        for row in raw_matrix
    ]

    print("Done.")
    return matrix, valid_addresses


def get_travel_time(
    matrix: list[list[float]],
    locations: list[str],
    from_addr: str,
    to_addr: str,
) -> float | None:
    """Look up travel time in minutes between two addresses."""
    try:
        i = locations.index(from_addr)
        j = locations.index(to_addr)
        return matrix[i][j]
    except ValueError:
        return None


def save_matrix(matrix: list[list[float]], locations: list[str], path: str) -> None:
    """Save the matrix and location list to a JSON file for caching."""
    with open(path, "w") as f:
        json.dump({"locations": locations, "matrix": matrix}, f, indent=2)


def load_matrix(path: str) -> tuple[list[list[float]], list[str]]:
    """Load a cached matrix from a JSON file."""
    with open(path) as f:
        data = json.load(f)
    return data["matrix"], data["locations"]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build travel time matrix from activities JSON")
    parser.add_argument("json_path", help="Path to activities JSON")
    parser.add_argument("--hotel", default=None, help="Hotel/start address")
    parser.add_argument("--profile", default="car", choices=["foot", "car", "bicycle"])
    parser.add_argument("--out", default="travel_matrix.json", help="Output file")
    args = parser.parse_args()

    matrix, locations = build_matrix(args.json_path, args.hotel, args.profile)
    save_matrix(matrix, locations, args.out)
    print(f"Saved {len(locations)}x{len(locations)} matrix to {args.out}")