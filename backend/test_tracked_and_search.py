import asyncio
import httpx
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

async def test_all():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=== 1. TESTING GET /api/tracked-routes ===")
        r_tracked = await client.get("http://localhost:8000/api/tracked-routes")
        print("Tracked Routes Status Code:", r_tracked.status_code)
        tracked_data = r_tracked.json()
        print(f"Total Tracked Routes: {len(tracked_data)}")
        for route in tracked_data[:3]:
            print(f"\nRoute ID {route['id']}: {route['origin']['code']} -> {route['destination']['code']} ({route['trip_type']})")
            print(f"  Estimated Price: S${route['estimated_price']}")
            if route.get("leg1"):
                l1 = route["leg1"]
                print(f"  Outbound Leg 1: {l1['origin']}->{l1['destination']} | {l1['airline']} {l1['flight_number']} ({l1['departure_time']} -> {l1['arrival_time']}) S${l1['price']}")
                print(f"    Platform Prices: {l1.get('platform_prices')} (Cheapest: {l1.get('cheapest_platform')})")
            if route.get("leg2"):
                l2 = route["leg2"]
                print(f"  Outbound Leg 2: {l2['origin']}->{l2['destination']} | {l2['airline']} {l2['flight_number']} ({l2['departure_time']} -> {l2['arrival_time']}) S${l2['price']}")
            if route.get("return_leg1"):
                r1 = route["return_leg1"]
                print(f"  Return Leg 1: {r1['origin']}->{r1['destination']} | {r1['airline']} {r1['flight_number']} ({r1['departure_time']} -> {r1['arrival_time']}) S${r1['price']}")
                print(f"    Platform Prices: {r1.get('platform_prices')} (Cheapest: {r1.get('cheapest_platform')})")
            if route.get("return_leg2"):
                r2 = route["return_leg2"]
                print(f"  Return Leg 2: {r2['origin']}->{r2['destination']} | {r2['airline']} {r2['flight_number']} ({r2['departure_time']} -> {r2['arrival_time']}) S${r2['price']}")

        print("\n=== 2. TESTING POST /api/flights/search ===")
        search_req = {
            "origin": "BWN",
            "destination": "KUL",
            "range_start": "2026-10-01",
            "range_end": "2026-10-31",
            "trip_duration_days": 10,
            "trip_type": "round_trip"
        }
        r_search = await client.post("http://localhost:8000/api/flights/search", json=search_req)
        print("Search API Status Code:", r_search.status_code)
        sdata = r_search.json()
        print("Direct Option:", sdata['direct_option']['airline'], "#" + str(sdata['direct_option']['flight_number']), "Price: S$" + str(sdata['direct_option']['price']))
        if sdata['direct_option']['legs']:
            dleg = sdata['direct_option']['legs'][0]
            print(f"  Direct Leg Schedule: {dleg['departure_time']} -> {dleg['arrival_time']} ({dleg['duration']})")
            print(f"  Direct Leg Platforms: {dleg.get('platform_prices')}")
        
        if sdata.get('split_options'):
            split1 = sdata['split_options'][0]
            print(f"Best Split via {split1['hub']['code']}: Total S${split1['total_price']}")
            print(f"  Leg 1 ({split1['leg1']['origin']}->{split1['leg1']['destination']}): {split1['leg1']['airline']} {split1['leg1']['flight_number']} ({split1['leg1']['departure_time']}->{split1['leg1']['arrival_time']}) S${split1['leg1']['price']}")
            print(f"    Leg 1 Platforms: {split1['leg1'].get('platform_prices')}")

if __name__ == "__main__":
    asyncio.run(test_all())
