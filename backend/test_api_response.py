import json, sys
sys.path.insert(0, '.')
import asyncio
from main import search_flight_routes, SearchRequest
from database import get_db, SessionLocal

async def test():
    db = SessionLocal()
    
    print("=== TEST 1: BWN -> TWU ===")
    req1 = SearchRequest(origin="BWN", destination="TWU", range_start="2026-10-01", range_end="2026-10-31", trip_duration_days=10)
    res1 = await search_flight_routes(req1, None, db)
    print(f"Direct available: {res1['direct_option']['has_direct_flight']}")
    print("Valid split hubs returned for BWN -> TWU:")
    for s in res1['split_options']:
        print(f"  - Hub: {s['hub']['code']} ({s['hub']['city']}) | Total Price: S${s['total_price']}")
    print()

    print("=== TEST 2: BWN -> CTS ===")
    req2 = SearchRequest(origin="BWN", destination="CTS", range_start="2026-10-01", range_end="2026-10-31", trip_duration_days=10)
    res2 = await search_flight_routes(req2, None, db)
    print(f"Direct available: {res2['direct_option']['has_direct_flight']}")
    print("Valid split hubs returned for BWN -> CTS:")
    for s in res2['split_options']:
        print(f"  - Hub: {s['hub']['code']} ({s['hub']['city']}) | Total Price: S${s['total_price']}")
    print()

    db.close()

asyncio.run(test())
