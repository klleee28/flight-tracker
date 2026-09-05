import math
from typing import List, Dict, Any, Optional

# Major Asian & Global Transit Hubs
HUBS: Dict[str, Dict[str, Any]] = {
    "KUL": {
        "code": "KUL",
        "name": "Kuala Lumpur International Airport",
        "city": "Kuala Lumpur",
        "country": "Malaysia",
        "latitude": 2.7456,
        "longitude": 101.7099,
        "hub_score": 0.95
    },
    "SIN": {
        "code": "SIN",
        "name": "Singapore Changi Airport",
        "city": "Singapore",
        "country": "Singapore",
        "latitude": 1.3644,
        "longitude": 103.9915,
        "hub_score": 0.98
    },
    "NRT": {
        "code": "NRT",
        "name": "Tokyo Narita International Airport",
        "city": "Tokyo",
        "country": "Japan",
        "latitude": 35.7720,
        "longitude": 140.3929,
        "hub_score": 0.94
    },
    "TPE": {
        "code": "TPE",
        "name": "Taiwan Taoyuan International Airport",
        "city": "Taipei",
        "country": "Taiwan",
        "latitude": 25.0797,
        "longitude": 121.2342,
        "hub_score": 0.90
    },
    "MNL": {
        "code": "MNL",
        "name": "Ninoy Aquino International Airport",
        "city": "Manila",
        "country": "Philippines",
        "latitude": 14.5086,
        "longitude": 121.0194,
        "hub_score": 0.85
    },
    "BKK": {
        "code": "BKK",
        "name": "Suvarnabhumi Airport",
        "city": "Bangkok",
        "country": "Thailand",
        "latitude": 13.6900,
        "longitude": 100.7501,
        "hub_score": 0.92
    },
    "HKG": {
        "code": "HKG",
        "name": "Hong Kong International Airport",
        "city": "Hong Kong",
        "country": "Hong Kong SAR",
        "latitude": 22.3080,
        "longitude": 113.9185,
        "hub_score": 0.93
    },
    "BKI": {
        "code": "BKI",
        "name": "Kota Kinabalu International Airport",
        "city": "Kota Kinabalu",
        "country": "Malaysia",
        "latitude": 5.9211,
        "longitude": 116.0512,
        "hub_score": 0.88
    }
}

# Extensive Global Airport Registry (Supports Global IATA Code Lookups)
AIRPORTS: Dict[str, Dict[str, Any]] = {
    **HUBS,
    "BWN": { "code": "BWN", "name": "Brunei International Airport", "city": "Bandar Seri Begawan", "country": "Brunei", "latitude": 4.9442, "longitude": 114.9283 },
    "CTS": { "code": "CTS", "name": "New Chitose Airport", "city": "Sapporo", "country": "Japan", "latitude": 42.7752, "longitude": 141.6923 },
    "TWU": { "code": "TWU", "name": "Tawau Airport", "city": "Tawau", "country": "Malaysia", "latitude": 4.3202, "longitude": 118.1219 },
    "ICN": { "code": "ICN", "name": "Incheon International Airport", "city": "Seoul", "country": "South Korea", "latitude": 37.4602, "longitude": 126.4407 },
    "DPS": { "code": "DPS", "name": "Ngurah Rai International Airport", "city": "Bali", "country": "Indonesia", "latitude": -8.7482, "longitude": 115.1672 },
    "CGK": { "code": "CGK", "name": "Soekarno-Hatta International Airport", "city": "Jakarta", "country": "Indonesia", "latitude": -6.1275, "longitude": 106.6537 },
    "PNH": { "code": "PNH", "name": "Phnom Penh International Airport", "city": "Phnom Penh", "country": "Cambodia", "latitude": 11.5466, "longitude": 104.8441 },
    "HAN": { "code": "HAN", "name": "Noi Bai International Airport", "city": "Hanoi", "country": "Vietnam", "latitude": 21.2212, "longitude": 105.8072 },
    "SGN": { "code": "SGN", "name": "Tan Son Nhat International Airport", "city": "Ho Chi Minh City", "country": "Vietnam", "latitude": 10.8188, "longitude": 106.6519 },
    "HKT": { "code": "HKT", "name": "Phuket International Airport", "city": "Phuket", "country": "Thailand", "latitude": 8.1132, "longitude": 98.3169 },
    "KIX": { "code": "KIX", "name": "Kansai International Airport", "city": "Osaka", "country": "Japan", "latitude": 34.4320, "longitude": 135.2304 },
    "HND": { "code": "HND", "name": "Tokyo Haneda Airport", "city": "Tokyo", "country": "Japan", "latitude": 35.5494, "longitude": 139.7798 },
    "SYD": { "code": "SYD", "name": "Sydney Kingsford Smith Airport", "city": "Sydney", "country": "Australia", "latitude": -33.9461, "longitude": 151.1772 },
    "MEL": { "code": "MEL", "name": "Melbourne Airport", "city": "Melbourne", "country": "Australia", "latitude": -37.6690, "longitude": 144.8410 },
    "LHR": { "code": "LHR", "name": "London Heathrow Airport", "city": "London", "country": "United Kingdom", "latitude": 51.4700, "longitude": -0.4543 },
    "JFK": { "code": "JFK", "name": "John F. Kennedy International Airport", "city": "New York", "country": "United States", "latitude": 40.6413, "longitude": -73.7781 },
    "LAX": { "code": "LAX", "name": "Los Angeles International Airport", "city": "Los Angeles", "country": "United States", "latitude": 33.9416, "longitude": -118.4085 },
    "DXB": { "code": "DXB", "name": "Dubai International Airport", "city": "Dubai", "country": "United Arab Emirates", "latitude": 25.2532, "longitude": 55.3657 }
}

# Known Real-World Operating Direct Routes (Flight Route Graph Matrix)
# Only flight routes in this set exist in real-world airline schedules.
KNOWN_DIRECT_ROUTES = {
    # BWN (Brunei) operating routes
    ("BWN", "KUL"), ("KUL", "BWN"),
    ("BWN", "SIN"), ("SIN", "BWN"),
    ("BWN", "MNL"), ("MNL", "BWN"),
    ("BWN", "BKK"), ("BKK", "BWN"),
    ("BWN", "HKG"), ("HKG", "BWN"),
    ("BWN", "TPE"), ("TPE", "BWN"),
    ("BWN", "NRT"), ("NRT", "BWN"),
    ("BWN", "BKI"), ("BKI", "BWN"),
    ("BWN", "CGK"), ("CGK", "BWN"),
    ("BWN", "LHR"), ("LHR", "BWN"),
    ("BWN", "DXB"), ("DXB", "BWN"),
    ("BWN", "MEL"), ("MEL", "BWN"),

    # KUL (Kuala Lumpur) operating routes
    ("KUL", "CTS"), ("CTS", "KUL"),
    ("KUL", "NRT"), ("NRT", "KUL"),
    ("KUL", "HND"), ("HND", "KUL"),
    ("KUL", "KIX"), ("KIX", "KUL"),
    ("KUL", "ICN"), ("ICN", "KUL"),
    ("KUL", "TPE"), ("TPE", "KUL"),
    ("KUL", "HKG"), ("HKG", "KUL"),
    ("KUL", "MNL"), ("MNL", "KUL"),
    ("KUL", "BKK"), ("BKK", "KUL"),
    ("KUL", "SIN"), ("SIN", "KUL"),
    ("KUL", "TWU"), ("TWU", "KUL"),
    ("KUL", "BKI"), ("BKI", "KUL"),
    ("KUL", "DPS"), ("DPS", "KUL"),
    ("KUL", "CGK"), ("CGK", "KUL"),
    ("KUL", "PNH"), ("PNH", "KUL"),
    ("KUL", "HAN"), ("HAN", "KUL"),
    ("KUL", "SGN"), ("SGN", "KUL"),
    ("KUL", "HKT"), ("HKT", "KUL"),
    ("KUL", "SYD"), ("SYD", "KUL"),
    ("KUL", "MEL"), ("MEL", "KUL"),
    ("KUL", "LHR"), ("LHR", "KUL"),
    ("KUL", "DXB"), ("DXB", "KUL"),

    # BKI (Kota Kinabalu) operating routes
    ("BKI", "TWU"), ("TWU", "BKI"),
    ("BKI", "KUL"), ("KUL", "BKI"),
    ("BKI", "SIN"), ("SIN", "BKI"),
    ("BKI", "HKG"), ("HKG", "BKI"),
    ("BKI", "TPE"), ("TPE", "BKI"),
    ("BKI", "NRT"), ("NRT", "BKI"),
    ("BKI", "ICN"), ("ICN", "BKI"),

    # SIN (Singapore) operating routes
    ("SIN", "CTS"), ("CTS", "SIN"),
    ("SIN", "NRT"), ("NRT", "SIN"),
    ("SIN", "HND"), ("HND", "SIN"),
    ("SIN", "KIX"), ("KIX", "SIN"),
    ("SIN", "ICN"), ("ICN", "SIN"),
    ("SIN", "TPE"), ("TPE", "SIN"),
    ("SIN", "HKG"), ("HKG", "SIN"),
    ("SIN", "MNL"), ("MNL", "SIN"),
    ("SIN", "BKK"), ("BKK", "SIN"),
    ("SIN", "DPS"), ("DPS", "SIN"),
    ("SIN", "CGK"), ("CGK", "SIN"),
    ("SIN", "PNH"), ("PNH", "SIN"),
    ("SIN", "HAN"), ("HAN", "SIN"),
    ("SIN", "SGN"), ("SGN", "SIN"),
    ("SIN", "HKT"), ("HKT", "SIN"),
    ("SIN", "SYD"), ("SYD", "SIN"),
    ("SIN", "MEL"), ("MEL", "SIN"),
    ("SIN", "LHR"), ("LHR", "SIN"),
    ("SIN", "DXB"), ("DXB", "SIN"),
    ("SIN", "JFK"), ("JFK", "SIN"),
    ("SIN", "LAX"), ("LAX", "SIN"),

    # TPE (Taipei) operating routes
    ("TPE", "CTS"), ("CTS", "TPE"),
    ("TPE", "NRT"), ("NRT", "TPE"),
    ("TPE", "HND"), ("HND", "TPE"),
    ("TPE", "KIX"), ("KIX", "TPE"),
    ("TPE", "ICN"), ("ICN", "TPE"),
    ("TPE", "HKG"), ("HKG", "TPE"),
    ("TPE", "MNL"), ("MNL", "TPE"),
    ("TPE", "BKK"), ("BKK", "TPE"),
    ("TPE", "DPS"), ("DPS", "TPE"),
    ("TPE", "SGN"), ("SGN", "TPE"),
    ("TPE", "HAN"), ("HAN", "TPE"),
    ("TPE", "LAX"), ("LAX", "TPE"),
    ("TPE", "JFK"), ("JFK", "TPE"),

    # BKK (Bangkok) operating routes
    ("BKK", "CTS"), ("CTS", "BKK"),
    ("BKK", "NRT"), ("NRT", "BKK"),
    ("BKK", "HND"), ("HND", "BKK"),
    ("BKK", "KIX"), ("KIX", "BKK"),
    ("BKK", "ICN"), ("ICN", "BKK"),
    ("BKK", "HKG"), ("HKG", "BKK"),
    ("BKK", "MNL"), ("MNL", "BKK"),
    ("BKK", "SGN"), ("SGN", "BKK"),
    ("BKK", "HAN"), ("HAN", "BKK"),
    ("BKK", "PNH"), ("PNH", "BKK"),
    ("BKK", "SYD"), ("SYD", "BKK"),
    ("BKK", "LHR"), ("LHR", "BKK"),
    ("BKK", "DXB"), ("DXB", "BKK"),

    # HKG (Hong Kong) operating routes
    ("HKG", "CTS"), ("CTS", "HKG"),
    ("HKG", "NRT"), ("NRT", "HKG"),
    ("HKG", "HND"), ("HND", "HKG"),
    ("HKG", "KIX"), ("KIX", "HKG"),
    ("HKG", "ICN"), ("ICN", "HKG"),
    ("HKG", "MNL"), ("MNL", "HKG"),
    ("HKG", "SGN"), ("SGN", "HKG"),
    ("HKG", "HAN"), ("HAN", "HKG"),
    ("HKG", "SYD"), ("SYD", "HKG"),
    ("HKG", "MEL"), ("MEL", "HKG"),
    ("HKG", "LHR"), ("LHR", "HKG"),
    ("HKG", "DXB"), ("DXB", "HKG"),
    ("HKG", "LAX"), ("LAX", "HKG"),
    ("HKG", "JFK"), ("JFK", "HKG"),

    # NRT / HND (Tokyo) operating routes
    ("NRT", "CTS"), ("CTS", "NRT"),
    ("HND", "CTS"), ("CTS", "HND"),
    ("NRT", "ICN"), ("ICN", "NRT"),
    ("NRT", "KIX"), ("KIX", "NRT"),
    ("NRT", "SYD"), ("SYD", "NRT"),
    ("NRT", "LAX"), ("LAX", "NRT"),
    ("NRT", "JFK"), ("JFK", "NRT"),

    # MNL (Manila) operating routes
    ("MNL", "NRT"), ("NRT", "MNL"),
    ("MNL", "HND"), ("HND", "MNL"),
    ("MNL", "KIX"), ("KIX", "MNL"),
    ("MNL", "ICN"), ("ICN", "MNL"),
    ("MNL", "SYD"), ("SYD", "MNL"),
    ("MNL", "LAX"), ("LAX", "MNL"),
    ("MNL", "JFK"), ("JFK", "MNL")
}

def has_direct_flight(origin: str, destination: str) -> bool:
    """Returns True only if a confirmed real-world direct flight schedule exists between origin and destination."""
    from services.scraper import FLIGHT_SCHEDULE_REGISTRY
    orig = origin.strip().upper()
    dest = destination.strip().upper()
    if orig == dest:
        return True
    return (orig, dest) in FLIGHT_SCHEDULE_REGISTRY

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates distance between two coordinates in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def get_airport_info(code: str) -> Dict[str, Any]:
    code_upper = code.strip().upper()
    if code_upper in AIRPORTS:
        return AIRPORTS[code_upper]
    return {
        "code": code_upper,
        "name": f"{code_upper} Airport",
        "city": code_upper,
        "country": "Global Destination",
        "latitude": 12.0,
        "longitude": 105.0
    }

def get_all_hubs() -> List[Dict[str, Any]]:
    return list(HUBS.values())

def find_split_routes(origin: str, destination: str) -> List[Dict[str, Any]]:
    """
    Given Origin and Destination, generates valid 2-leg split routes passing through transit hubs.
    STRICTLY filters out phantom routes: Leg 1 (Origin -> Hub) AND Leg 2 (Hub -> Destination)
    MUST BOTH BE REAL-WORLD OPERATING DIRECT FLIGHT ROUTES.
    """
    orig_code = origin.strip().upper()
    dest_code = destination.strip().upper()
    
    orig_info = get_airport_info(orig_code)
    dest_info = get_airport_info(dest_code)

    direct_dist = haversine_distance(
        orig_info.get("latitude", 10.0), orig_info.get("longitude", 105.0),
        dest_info.get("latitude", 10.0), dest_info.get("longitude", 105.0)
    )

    candidates = []

    for hub_code, hub_info in HUBS.items():
        if hub_code == orig_code or hub_code == dest_code:
            continue
        
        # STRICT REAL-WORLD ROUTE GRAPH CHECK
        # Leg 1 (origin -> hub) and Leg 2 (hub -> destination) MUST both operate in real life!
        if not has_direct_flight(orig_code, hub_code) or not has_direct_flight(hub_code, dest_code):
            continue

        leg1_dist = haversine_distance(
            orig_info.get("latitude", 10.0), orig_info.get("longitude", 105.0),
            hub_info["latitude"], hub_info["longitude"]
        )
        leg2_dist = haversine_distance(
            hub_info["latitude"], hub_info["longitude"],
            dest_info.get("latitude", 10.0), dest_info.get("longitude", 105.0)
        )
        total_dist = leg1_dist + leg2_dist

        detour_ratio = round(total_dist / max(direct_dist, 1.0), 2)
        max_detour = 15.0 if direct_dist < 1000 else 2.8

        if detour_ratio <= max_detour:
            candidates.append({
                "hub": hub_info,
                "leg1": {"origin": orig_code, "destination": hub_code, "distance_km": round(leg1_dist)},
                "leg2": {"origin": hub_code, "destination": dest_code, "distance_km": round(leg2_dist)},
                "total_distance_km": round(total_dist),
                "detour_ratio": detour_ratio
            })

    candidates.sort(key=lambda x: x["detour_ratio"])
    return candidates

def build_split_route_options(origin: str, destination: str) -> List[Dict[str, Any]]:
    return find_split_routes(origin, destination)
