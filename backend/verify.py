import asyncio
import httpx
import json
import sys

# Ensure UTF-8 output encoding for Windows terminal
sys.stdout.reconfigure(encoding='utf-8')

async def verify():
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Test root endpoint
        r_root = await client.get("http://localhost:8000/")
        print("Root Endpoint:", r_root.status_code, r_root.json())

        # 2. Test hubs endpoint
        r_hubs = await client.get("http://localhost:8000/api/hubs")
        print(f"Hubs Endpoint ({len(r_hubs.json())} hubs):", r_hubs.status_code)

        # 3. Test flight search endpoint (BWN to CTS)
        payload = {"origin": "BWN", "destination": "CTS", "target_month": "2026-10"}
        r_search = await client.post("http://localhost:8000/api/flights/search", json=payload)
        print("Search API Status:", r_search.status_code)
        
        data = r_search.json()
        print("\n--- DIRECT ROUTE BENCHMARK ---")
        print(f"Airline: {data['direct_option']['airline']} #{data['direct_option']['flight_number']}")
        print(f"Direct Price: ${data['direct_option']['price']} USD")
        print(f"60-Day Avg: ${data['direct_option']['avg_60d']} USD")
        print(f"Deal Badge: {data['direct_option']['deal_info']['badge']}")
        
        print("\n--- AI 2-LEG SPLIT ROUTE MATRIX ---")
        for i, opt in enumerate(data['split_options'], 1):
            print(f"[{i}] Transit Hub: {opt['hub']['city']} ({opt['hub']['code']}) | Total Split Price: ${opt['total_price']} USD")
            print(f"    Leg 1 ({opt['leg1']['origin']} ➔ {opt['leg1']['destination']}): ${opt['leg1']['price']} ({opt['leg1']['airline']})")
            print(f"    Leg 2 ({opt['leg2']['origin']} ➔ {opt['leg2']['destination']}): ${opt['leg2']['price']} ({opt['leg2']['airline']})")
            print(f"    Savings vs Direct: ${opt['savings_vs_direct']} ({opt['savings_pct_vs_direct']}%)")
            print(f"    Deal Score: {opt['deal_info']['badge']} ({opt['deal_info']['message']})")

if __name__ == "__main__":
    asyncio.run(verify())
