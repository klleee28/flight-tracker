import asyncio
import re
from playwright.async_api import async_playwright

async def parse_google_flights_live(origin: str, destination: str, travel_date: str):
    user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    url = f'https://www.google.com/travel/flights?q=Flights+from+{origin}+to+{destination}+on+{travel_date}&curr=SGD&hl=en'
    
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=user_agent)
        try:
            await page.goto(url, wait_until='domcontentloaded', timeout=20000)
            await page.wait_for_timeout(4000)
            
            text = await page.inner_text('body')
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            
            i = 0
            while i < len(lines):
                if re.match(r'^\d{1,2}:\d{2}\s*(?:AM|PM)$', lines[i], re.IGNORECASE):
                    try:
                        dep_time = lines[i]
                        arr_idx = i + 1
                        if lines[arr_idx] in ['-', '–', '—', '']:
                            arr_idx = i + 2
                        arr_time = lines[arr_idx]
                        
                        airline = lines[arr_idx + 1]
                        duration = lines[arr_idx + 2]
                        route_str = lines[arr_idx + 3]
                        stop_type = lines[arr_idx + 4]
                        
                        price_val = 0.0
                        for offset in range(3, 10):
                            if arr_idx + offset < len(lines):
                                line_txt = lines[arr_idx + offset]
                                pm = re.search(r'SGD\s?([\d,]+)', line_txt)
                                if pm:
                                    price_val = float(pm.group(1).replace(',', ''))
                                    break
                        
                        if price_val > 0 and ('Nonstop' in stop_type or 'stop' in stop_type):
                            results.append({
                                'origin': origin,
                                'destination': destination,
                                'airline': airline,
                                'departure_time': dep_time,
                                'arrival_time': arr_time,
                                'duration': duration,
                                'stop_type': stop_type,
                                'price_sgd': price_val,
                                'source': 'Google Flights Live'
                            })
                            i = arr_idx + 5
                            continue
                    except Exception:
                        pass
                i += 1
        finally:
            await browser.close()
            
    return results

async def main():
    res1 = await parse_google_flights_live('BWN', 'KUL', '2026-10-15')
    print('BWN -> KUL Live Results:', res1)
    res2 = await parse_google_flights_live('KUL', 'NRT', '2026-10-15')
    print('KUL -> NRT Live Results:', res2)

if __name__ == '__main__':
    asyncio.run(main())
