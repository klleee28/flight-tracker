import asyncio, sys, json
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from database import SessionLocal
from models import TrackedRoute, PriceHistory
from services.graph import get_airport_info, has_direct_flight, build_split_route_options
from services.scraper import fetch_route_price, parse_time_to_minutes
from services.deals import calculate_route_statistics, evaluate_deal_score
from datetime import datetime

async def scrape_route(r, db):
    print(f"Scraping route {r.id}: {r.origin} -> {r.destination} ({r.range_start} to {r.range_end})...")
    orig_info = get_airport_info(r.origin)
    dest_info = get_airport_info(r.destination)
    is_direct = has_direct_flight(r.origin, r.destination)
    is_round_trip = (r.trip_type or 'round_trip').lower().strip() != 'one_way'

    outbound_date = r.range_start or '2026-09-24'
    return_date = r.range_end or '2026-10-01'

    splits = build_split_route_options(r.origin, r.destination)
    best_hub = splits[0]['hub']['code'] if splits else ('DIRECT' if is_direct else 'N/A')

    return_splits = build_split_route_options(r.destination, r.origin) if is_round_trip else []
    return_best_hub = return_splits[0]['hub']['code'] if return_splits else ('DIRECT' if is_direct else 'N/A')

    leg1_detail = None
    leg2_detail = None
    outbound_price = 0.0
    now = datetime.utcnow()

    if is_direct:
        # Outbound leg is one-way
        direct_data = await fetch_route_price(r.origin, r.destination, outbound_date, allow_live_browser=True, is_round_trip=False)
        if direct_data.get('is_available') and direct_data.get('price', 0) > 0:
            outbound_price = round(direct_data['price'], 2)
            leg1_detail = {
                'origin': r.origin, 'destination': r.destination,
                'airline': direct_data['airline'], 'flight_number': direct_data['flight_number'],
                'departure_date': direct_data.get('departure_date', outbound_date),
                'departure_time': direct_data['departure_time'], 'arrival_time': direct_data['arrival_time'],
                'duration': direct_data['duration'], 'price': outbound_price,
                'platform_prices': direct_data.get('platform_prices', {}),
                'cheapest_platform': direct_data.get('cheapest_platform', ''),
            }
            db.add(PriceHistory(
                origin=r.origin, destination=r.destination, airline=direct_data['airline'],
                flight_number=direct_data['flight_number'], departure_date=outbound_date,
                price=outbound_price, currency='SGD', is_direct=True, scraped_at=now
            ))
    elif splits:
        split = splits[0]
        leg1_data = await fetch_route_price(r.origin, best_hub, outbound_date, split['leg1']['distance_km'], allow_live_browser=True, is_round_trip=False)
        leg1_arr_mins = parse_time_to_minutes(leg1_data.get('arrival_time'))
        min_dep_2 = (leg1_arr_mins + 45) if leg1_arr_mins is not None else None

        leg2_data = await fetch_route_price(best_hub, r.destination, outbound_date, split['leg2']['distance_km'], allow_live_browser=True, min_dep_minutes=min_dep_2, is_round_trip=False)

        if leg1_data.get('is_available') and leg2_data.get('is_available'):
            outbound_price = round(leg1_data['price'] + leg2_data['price'], 2)
            leg1_detail = {
                'origin': r.origin, 'destination': best_hub,
                'airline': leg1_data['airline'], 'flight_number': leg1_data['flight_number'],
                'departure_date': leg1_data.get('departure_date', outbound_date),
                'departure_time': leg1_data['departure_time'], 'arrival_time': leg1_data['arrival_time'],
                'duration': leg1_data['duration'], 'price': round(leg1_data['price'], 2),
                'platform_prices': leg1_data.get('platform_prices', {}),
                'cheapest_platform': leg1_data.get('cheapest_platform', ''),
            }
            leg2_detail = {
                'origin': best_hub, 'destination': r.destination,
                'airline': leg2_data['airline'], 'flight_number': leg2_data['flight_number'],
                'departure_date': leg2_data.get('departure_date', outbound_date),
                'departure_time': leg2_data['departure_time'], 'arrival_time': leg2_data['arrival_time'],
                'duration': leg2_data['duration'], 'price': round(leg2_data['price'], 2),
                'platform_prices': leg2_data.get('platform_prices', {}),
                'cheapest_platform': leg2_data.get('cheapest_platform', ''),
            }
            db.add(PriceHistory(
                origin=r.origin, destination=best_hub, airline=leg1_data['airline'],
                flight_number=leg1_data['flight_number'], departure_date=outbound_date,
                price=round(leg1_data['price'], 2), currency='SGD', is_direct=True, scraped_at=now
            ))
            db.add(PriceHistory(
                origin=best_hub, destination=r.destination, airline=leg2_data['airline'],
                flight_number=leg2_data['flight_number'], departure_date=outbound_date,
                price=round(leg2_data['price'], 2), currency='SGD', is_direct=True, scraped_at=now
            ))

    return_leg1_detail = None
    return_leg2_detail = None
    return_price = 0.0

    if is_round_trip:
        is_return_direct = has_direct_flight(r.destination, r.origin)
        if is_return_direct:
            ret_direct_data = await fetch_route_price(r.destination, r.origin, return_date, allow_live_browser=True, is_round_trip=False)
            if ret_direct_data.get('is_available') and ret_direct_data.get('price', 0) > 0:
                return_price = round(ret_direct_data['price'], 2)
                return_leg1_detail = {
                    'origin': r.destination, 'destination': r.origin,
                    'airline': ret_direct_data['airline'], 'flight_number': ret_direct_data['flight_number'],
                    'departure_date': ret_direct_data.get('departure_date', return_date),
                    'departure_time': ret_direct_data['departure_time'], 'arrival_time': ret_direct_data['arrival_time'],
                    'duration': ret_direct_data['duration'], 'price': return_price,
                    'platform_prices': ret_direct_data.get('platform_prices', {}),
                    'cheapest_platform': ret_direct_data.get('cheapest_platform', ''),
                }
                db.add(PriceHistory(
                    origin=r.destination, destination=r.origin, airline=ret_direct_data['airline'],
                    flight_number=ret_direct_data['flight_number'], departure_date=return_date,
                    price=return_price, currency='SGD', is_direct=True, scraped_at=now
                ))
        elif return_splits:
            ret_split = return_splits[0]
            ret_leg1_data = await fetch_route_price(r.destination, return_best_hub, return_date, ret_split['leg1']['distance_km'], allow_live_browser=True, is_round_trip=False)
            ret_leg1_arr_mins = parse_time_to_minutes(ret_leg1_data.get('arrival_time'))
            min_ret_dep_2 = (ret_leg1_arr_mins + 45) if ret_leg1_arr_mins is not None else None

            ret_leg2_data = await fetch_route_price(return_best_hub, r.origin, return_date, ret_split['leg2']['distance_km'], allow_live_browser=True, min_dep_minutes=min_ret_dep_2, is_round_trip=False)

            if ret_leg1_data.get('is_available') and ret_leg2_data.get('is_available'):
                return_price = round(ret_leg1_data['price'] + ret_leg2_data['price'], 2)
                return_leg1_detail = {
                    'origin': r.destination, 'destination': return_best_hub,
                    'airline': ret_leg1_data['airline'], 'flight_number': ret_leg1_data['flight_number'],
                    'departure_date': ret_leg1_data.get('departure_date', return_date),
                    'departure_time': ret_leg1_data['departure_time'], 'arrival_time': ret_leg1_data['arrival_time'],
                    'duration': ret_leg1_data['duration'], 'price': round(ret_leg1_data['price'], 2),
                    'platform_prices': ret_leg1_data.get('platform_prices', {}),
                    'cheapest_platform': ret_leg1_data.get('cheapest_platform', ''),
                }
                return_leg2_detail = {
                    'origin': return_best_hub, 'destination': r.origin,
                    'airline': ret_leg2_data['airline'], 'flight_number': ret_leg2_data['flight_number'],
                    'departure_date': ret_leg2_data.get('departure_date', return_date),
                    'departure_time': ret_leg2_data['departure_time'], 'arrival_time': ret_leg2_data['arrival_time'],
                    'duration': ret_leg2_data['duration'], 'price': round(ret_leg2_data['price'], 2),
                    'platform_prices': ret_leg2_data.get('platform_prices', {}),
                    'cheapest_platform': ret_leg2_data.get('cheapest_platform', ''),
                }
                db.add(PriceHistory(
                    origin=r.destination, destination=return_best_hub, airline=ret_leg1_data['airline'],
                    flight_number=ret_leg1_data['flight_number'], departure_date=return_date,
                    price=round(ret_leg1_data['price'], 2), currency='SGD', is_direct=True, scraped_at=now
                ))
                db.add(PriceHistory(
                    origin=return_best_hub, destination=r.origin, airline=ret_leg2_data['airline'],
                    flight_number=ret_leg2_data['flight_number'], departure_date=return_date,
                    price=round(ret_leg2_data['price'], 2), currency='SGD', is_direct=True, scraped_at=now
                ))

    stats = calculate_route_statistics(db, r.origin, r.destination)
    estimated_price = round(outbound_price + return_price, 2)
    deal_info = evaluate_deal_score(estimated_price, stats['avg_60d'], stats['avg_30d'])

    route_data = {
        'id': r.id,
        'origin': orig_info,
        'destination': dest_info,
        'range_start': r.range_start,
        'range_end': r.range_end,
        'trip_duration_days': r.trip_duration_days,
        'trip_type': r.trip_type,
        'has_direct_flight': is_direct,
        'best_hub': best_hub,
        'estimated_price': estimated_price,
        'avg_60d': stats['avg_60d'],
        'deal_info': deal_info,
        'leg1': leg1_detail,
        'leg2': leg2_detail,
        'return_leg1': return_leg1_detail,
        'return_leg2': return_leg2_detail,
        'is_active': r.is_active,
        'created_at': r.created_at.isoformat() if r.created_at else datetime.utcnow().isoformat()
    }

    r.cached_flight_data = json.dumps(route_data)
    r.last_scraped_at = now
    db.commit()
    print(f"SUCCESS: Route {r.id} ({r.origin}->{r.destination}) cached with accurate price: S${estimated_price}")

async def main():
    db = SessionLocal()
    active_routes = db.query(TrackedRoute).filter(TrackedRoute.is_active == True).all()
    for r in active_routes:
        await scrape_route(r, db)
    db.close()

if __name__ == '__main__':
    asyncio.run(main())
