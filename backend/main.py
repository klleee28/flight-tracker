import sys
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from database import engine, Base, get_db
from sqlalchemy.orm import Session
from models import Hub, Route, PriceHistory, TrackedRoute
from services.graph import HUBS as ASIAN_HUBS, build_split_route_options, get_airport_info, has_direct_flight
from services.scraper import fetch_route_price
from services.deals import calculate_route_statistics, evaluate_deal_score
from services.scheduler import (
    start_scheduler,
    stop_scheduler,
    get_scheduler_status,
    configure_daily_schedule,
    daily_tracked_routes_scraper_job,
    async_daily_tracked_routes_scraper_job,
    refresh_tracked_route_data
)
from services.scraper import LCC_AIRLINES, build_platform_price_breakdown

# Create DB tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AeroSplit AI Flight Tracker API",
    description="Automated Asian Transit Hub Split Routing & Deal Intelligence API",
    version="1.0.0"
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    db = SessionLocal_init()
    try:
        for code, hub in ASIAN_HUBS.items():
            existing = db.query(Hub).filter(Hub.code == code).first()
            if not existing:
                db.add(Hub(
                    code=code,
                    name=hub["name"],
                    city=hub["city"],
                    country=hub["country"],
                    latitude=hub["latitude"],
                    longitude=hub["longitude"],
                    is_active=True
                ))
        
        existing_tracked = db.query(TrackedRoute).count()
        if existing_tracked == 0:
            d_start = (datetime.utcnow() + timedelta(days=20)).strftime("%Y-%m-%d")
            d_end = (datetime.utcnow() + timedelta(days=27)).strftime("%Y-%m-%d")
            default_routes = [
                {"origin": "BWN", "destination": "TWU", "range_start": d_start, "range_end": d_end, "trip_duration_days": 7, "trip_type": "round_trip"},
                {"origin": "BWN", "destination": "KUL", "range_start": d_start, "range_end": d_end, "trip_duration_days": 7, "trip_type": "round_trip"},
                {"origin": "SIN", "destination": "CTS", "range_start": d_start, "range_end": d_end, "trip_duration_days": 10, "trip_type": "round_trip"},
                {"origin": "KUL", "destination": "NRT", "range_start": d_start, "range_end": d_end, "trip_duration_days": 10, "trip_type": "round_trip"},
            ]
            for r in default_routes:
                db.add(TrackedRoute(**r))

        db.commit()
    except Exception as e:
        print(f"Startup DB init notice: {e}")
    finally:
        db.close()
        
    start_scheduler()

def SessionLocal_init():
    from database import SessionLocal
    return SessionLocal()

@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()

class SearchRequest(BaseModel):
    origin: str
    destination: str
    range_start: Optional[str] = "2026-10-01"
    range_end: Optional[str] = "2026-10-31"
    trip_duration_days: Optional[int] = 10
    departure_date: Optional[str] = None
    return_date: Optional[str] = None
    trip_type: Optional[str] = "round_trip"

class CreateTrackedRouteRequest(BaseModel):
    origin: str
    destination: str
    range_start: Optional[str] = "2026-10-01"
    range_end: Optional[str] = "2026-10-31"
    trip_duration_days: Optional[int] = 10
    trip_type: Optional[str] = "round_trip"

class SchedulerConfigRequest(BaseModel):
    daily_time: str

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "AeroSplit AI Backend",
        "hubs_tracked": len(ASIAN_HUBS),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/hubs")
def get_hubs(db: Session = Depends(get_db)):
    hubs = db.query(Hub).filter(Hub.is_active == True).all()
    return hubs

@app.get("/api/scheduler/status")
def get_schedule_status():
    """
    Returns daily cron schedule status, next execution time, and tracked route count.
    """
    return get_scheduler_status()

@app.post("/api/scheduler/config")
def update_schedule_config(req: SchedulerConfigRequest):
    """
    Updates the daily recurring refresh schedule time (e.g., "02:00").
    """
    if not req.daily_time or ":" not in req.daily_time:
        raise HTTPException(status_code=400, detail="Time string in format HH:MM required (e.g., 02:00).")
    
    configure_daily_schedule(req.daily_time)
    return get_scheduler_status()

@app.post("/api/scheduler/trigger-now")
async def trigger_schedule_now():
    """
    Triggers an immediate background price refresh for all active tracked routes.
    """
    res = await async_daily_tracked_routes_scraper_job()
    return {
        "status": "success",
        "message": f"Daily background refresh executed. Refreshed {res.get('routes_count', 0)} active routes ({res.get('records_count', 0)} authentic price records updated).",
        "details": res,
        "triggered_at": datetime.utcnow().isoformat()
    }

@app.get("/api/tracked-routes")
async def get_tracked_routes(refresh: bool = False, db: Session = Depends(get_db)):
    import json
    routes = db.query(TrackedRoute).filter(TrackedRoute.is_active == True).all()
    from services.scraper import parse_time_to_minutes

    async def process_route(r):
        # 1. Return cached authentic flight details instantly if available
        if not refresh and r.cached_flight_data:
            try:
                cached = json.loads(r.cached_flight_data)
                stats = calculate_route_statistics(db, r.origin, r.destination)
                est_price = cached.get("estimated_price", 0.0)
                deal_info = evaluate_deal_score(est_price, stats["avg_60d"], stats["avg_30d"])
                cached["avg_60d"] = stats["avg_60d"]
                cached["deal_info"] = deal_info
                return cached
            except Exception as e:
                print(f"Notice: cached data parse error for route {r.id}: {e}")

        # 2. Live scrape with authentic bundled round-trip pricing and synchronized split routing
        return await refresh_tracked_route_data(r, db)

    tasks = [process_route(r) for r in routes]
    results = await asyncio.gather(*tasks) if tasks else []
    return results

@app.post("/api/tracked-routes")
async def create_tracked_route(req: CreateTrackedRouteRequest, db: Session = Depends(get_db)):
    orig = req.origin.strip().upper()
    dest = req.destination.strip().upper()
    
    if not orig or not dest:
        raise HTTPException(status_code=400, detail="Origin and Destination airport codes required.")

    existing = db.query(TrackedRoute).filter(
        TrackedRoute.origin == orig,
        TrackedRoute.destination == dest,
        TrackedRoute.is_active == True
    ).first()

    if existing:
        existing.range_start = req.range_start or "2026-10-01"
        existing.range_end = req.range_end or "2026-10-31"
        existing.trip_duration_days = req.trip_duration_days or 10
        existing.trip_type = req.trip_type or "round_trip"
        existing.cached_flight_data = None
        db.commit()
        db.refresh(existing)
        target_route = existing
    else:
        new_route = TrackedRoute(
            origin=orig,
            destination=dest,
            range_start=req.range_start or "2026-10-01",
            range_end=req.range_end or "2026-10-31",
            trip_duration_days=req.trip_duration_days or 10,
            trip_type=req.trip_type or "round_trip",
            is_active=True
        )
        db.add(new_route)
        db.commit()
        db.refresh(new_route)
        target_route = new_route

    # Immediately scrape and populate authentic price or no_route diagnostic
    from services.scheduler import refresh_tracked_route_data
    route_dict = await refresh_tracked_route_data(target_route, db)
    return route_dict

@app.delete("/api/tracked-routes/{route_id}")
def delete_tracked_route(route_id: int, db: Session = Depends(get_db)):
    route = db.query(TrackedRoute).filter(TrackedRoute.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Tracked route not found.")
    
    route.is_active = False
    db.commit()
    return {"status": "deleted", "id": route_id}

async def build_route_options(origin: str, destination: str, travel_date: str, db: Session):
    from services.scraper import parse_time_to_minutes
    is_direct_available = has_direct_flight(origin, destination)

    if is_direct_available:
        direct_data = await fetch_route_price(origin, destination, travel_date, allow_live_browser=True)
        direct_stats = calculate_route_statistics(db, origin, destination)
        direct_deal = evaluate_deal_score(direct_data["price"], direct_stats["avg_60d"], direct_stats["avg_30d"])

        captured_scraper_status = direct_data.get("scraper_status", {
            "is_live": True,
            "source": "Google Flights Live Web Search",
            "status_badge": "🟢 Verified Live Google Flights Engine",
            "message": "Real-time live rate & timetable scraped directly from Google Flights."
        })

        direct_option = {
            "is_direct": True,
            "has_direct_flight": True,
            "airline": direct_data["airline"],
            "flight_number": direct_data["flight_number"],
            "price": direct_data["price"],
            "avg_60d": direct_stats["avg_60d"],
            "avg_30d": direct_stats["avg_30d"],
            "deal_info": direct_deal,
            "legs": [{
                "origin": origin,
                "destination": destination,
                "airline": direct_data["airline"],
                "flight_number": direct_data["flight_number"],
                "price": direct_data["price"],
                "departure_date": direct_data.get("departure_date", travel_date),
                "departure_time": direct_data.get("departure_time", "09:15"),
                "arrival_time": direct_data.get("arrival_time", "16:45"),
                "duration": direct_data.get("duration", "7h 30m"),
                "platform_prices": direct_data.get("platform_prices", {}),
                "cheapest_platform": direct_data.get("cheapest_platform", "")
            }]
        }
    else:
        captured_scraper_status = {
            "is_live": False,
            "source": "route_registry",
            "status_badge": "⚡ Route Registry Verified",
            "message": f"No direct non-stop flights operate between {origin} and {destination}. Transit split required."
        }
        direct_option = {
            "is_direct": False,
            "has_direct_flight": False,
            "airline": "No Direct Non-Stop Flight",
            "flight_number": "N/A",
            "price": 0.0,
            "avg_60d": 0.0,
            "avg_30d": 0.0,
            "deal_info": {
                "score": "REGULAR_PRICE",
                "tier": "yellow",
                "badge": "No Direct Flight",
                "is_great_deal": False,
                "discount_pct": 0,
                "message": f"No direct non-stop flights operate between {origin} and {destination}. Split transit route required."
            },
            "legs": []
        }

    raw_splits = build_split_route_options(origin, destination)
    split_options = []

    for split in raw_splits:
        hub_code = split["hub"]["code"]
        leg1_data = await fetch_route_price(origin, hub_code, travel_date, split["leg1"]["distance_km"], allow_live_browser=True)
        if not leg1_data.get("is_available") or leg1_data["price"] <= 0:
            continue

        leg1_arr_mins = parse_time_to_minutes(leg1_data.get("arrival_time"))
        min_dep_2 = (leg1_arr_mins + 45) if leg1_arr_mins is not None else None

        leg2_data = await fetch_route_price(hub_code, destination, travel_date, split["leg2"]["distance_km"], allow_live_browser=True, min_dep_minutes=min_dep_2)
        if not leg2_data.get("is_available") or leg2_data["price"] <= 0:
            continue

        total_split_price = round(leg1_data["price"] + leg2_data["price"], 2)
        
        stats1 = calculate_route_statistics(db, origin, hub_code)
        stats2 = calculate_route_statistics(db, split["hub"]["code"], destination)
        combined_60d = round(stats1["avg_60d"] + stats2["avg_60d"], 2)
        combined_30d = round(stats1["avg_30d"] + stats2["avg_30d"], 2)

        deal_info = evaluate_deal_score(total_split_price, combined_60d, combined_30d)
        
        if is_direct_available:
            savings = round(direct_option["price"] - total_split_price, 2)
            savings_pct = round((savings / direct_option["price"]) * 100, 1) if direct_option["price"] > 0 else 0.0
        else:
            savings = 0.0
            savings_pct = 0.0

        leg1_dep_mins = parse_time_to_minutes(leg1_data.get("departure_time"))
        leg2_dep_mins = parse_time_to_minutes(leg2_data.get("departure_time"))
        leg2_arr_mins = parse_time_to_minutes(leg2_data.get("arrival_time"))

        if leg1_arr_mins is not None and leg2_dep_mins is not None:
            if leg2_dep_mins >= leg1_arr_mins:
                layover_mins = leg2_dep_mins - leg1_arr_mins
            else:
                layover_mins = (leg2_dep_mins + 1440) - leg1_arr_mins
        else:
            layover_mins = 120

        lay_h = layover_mins // 60
        lay_m = layover_mins % 60
        layover_str = f"{lay_h}h {lay_m:02d}m layover"

        if leg1_dep_mins is not None and leg2_arr_mins is not None:
            if leg2_arr_mins >= leg1_dep_mins and not leg2_data.get("is_next_day"):
                total_mins = leg2_arr_mins - leg1_dep_mins
            else:
                total_mins = (leg2_arr_mins + 1440) - leg1_dep_mins
            tot_h = total_mins // 60
            tot_m = total_mins % 60
            total_duration_str = f"{tot_h}h {tot_m:02d}m total"
        else:
            total_duration_str = "N/A"

        split_options.append({
            "hub": get_airport_info(hub_code),
            "total_price": total_split_price,
            "avg_60d": combined_60d,
            "avg_30d": combined_30d,
            "deal_info": deal_info,
            "savings_vs_direct": savings,
            "savings_pct_vs_direct": savings_pct,
            "is_best_split": False,
            "detour_ratio": split["detour_ratio"],
            "layover_duration": layover_str,
            "total_duration": total_duration_str,
            "leg1": {
                "origin": origin,
                "destination": hub_code,
                "airline": leg1_data["airline"],
                "flight_number": leg1_data["flight_number"],
                "price": round(leg1_data["price"], 2),
                "departure_date": leg1_data.get("departure_date", travel_date),
                "departure_time": leg1_data.get("departure_time", "08:00"),
                "arrival_time": leg1_data.get("arrival_time", "11:30"),
                "duration": leg1_data.get("duration", "3h 30m"),
                "platform_prices": leg1_data.get("platform_prices", {}),
                "cheapest_platform": leg1_data.get("cheapest_platform", "")
            },
            "leg2": {
                "origin": hub_code,
                "destination": destination,
                "airline": leg2_data["airline"],
                "flight_number": leg2_data["flight_number"],
                "price": round(leg2_data["price"], 2),
                "departure_date": leg2_data.get("departure_date", travel_date),
                "departure_time": leg2_data.get("departure_time", "15:15"),
                "arrival_time": leg2_data.get("arrival_time", "21:00"),
                "duration": leg2_data.get("duration", "5h 45m"),
                "platform_prices": leg2_data.get("platform_prices", {}),
                "cheapest_platform": leg2_data.get("cheapest_platform", "")
            }
        })

    split_options.sort(key=lambda x: x["total_price"])
    if split_options:
        split_options[0]["is_best_split"] = True

    return direct_option, split_options, captured_scraper_status

@app.post("/api/flights/search")
async def search_flight_routes(
    req: SearchRequest,
    db: Session = Depends(get_db)
):
    orig = req.origin.strip().upper()
    dest = req.destination.strip().upper()
    
    if not orig or not dest:
        raise HTTPException(status_code=400, detail="Origin and Destination airport codes required.")

    normalized_trip_type = (req.trip_type or "round_trip").lower().strip()
    is_round_trip = normalized_trip_type != "one_way"

    start_dt = datetime.strptime(req.range_start or "2026-10-01", "%Y-%m-%d")
    end_dt = datetime.strptime(req.range_end or "2026-10-31", "%Y-%m-%d")
    duration = req.trip_duration_days or 10

    total_days = max(1, (end_dt - start_dt).days - duration)
    sample_offsets = [0, total_days // 3, (total_days * 2) // 3, total_days]

    best_candidate_price = float("inf")
    best_candidate_idx = 0

    date_candidates_summary = []

    try:
        outbound_date = req.departure_date or req.range_start or "2026-10-15"
        return_date = req.return_date or (
            (datetime.strptime(outbound_date, "%Y-%m-%d") + timedelta(days=duration)).strftime("%Y-%m-%d")
            if is_round_trip else None
        )

        outbound_direct, outbound_splits, scraper_status = await build_route_options(orig, dest, outbound_date, db)

        return_direct = None
        return_splits = None
        total_rt_direct = outbound_direct["price"] if outbound_direct["has_direct_flight"] else 0.0
        total_rt_split = outbound_splits[0]["total_price"] if outbound_splits else (outbound_direct["price"] if outbound_direct["has_direct_flight"] else 0.0)
        
        combined_60d_avg_direct = outbound_direct["avg_60d"]
        combined_60d_avg_split = outbound_splits[0]["avg_60d"] if outbound_splits else outbound_direct["avg_60d"]

        if is_round_trip:
            return_direct, return_splits, _ = await build_route_options(dest, orig, return_date, db)
            if outbound_direct["has_direct_flight"] and return_direct["has_direct_flight"]:
                # Query genuine bundled round-trip fare directly from Google Flights
                rt_direct = await fetch_route_price(
                    orig, dest, outbound_date, return_date=return_date, is_round_trip=True, allow_live_browser=True
                )
                if rt_direct.get("is_available") and rt_direct.get("price", 0) > 0:
                    total_rt_direct = round(rt_direct["price"], 2)
                    ob_share = round(total_rt_direct / 2, 2)
                    ret_share = round(total_rt_direct - ob_share, 2)
                    outbound_direct["price"] = ob_share
                    return_direct["price"] = ret_share
                    if outbound_direct.get("legs"):
                        outbound_direct["legs"][0]["price"] = ob_share
                        outbound_direct["legs"][0]["airline"] = rt_direct["airline"]
                        outbound_direct["legs"][0]["departure_time"] = rt_direct.get("departure_time", outbound_direct["legs"][0]["departure_time"])
                        outbound_direct["legs"][0]["arrival_time"] = rt_direct.get("arrival_time", outbound_direct["legs"][0]["arrival_time"])
                        outbound_direct["legs"][0]["duration"] = rt_direct.get("duration", outbound_direct["legs"][0]["duration"])
                        is_ob_lcc = rt_direct["airline"] in LCC_AIRLINES
                        outbound_direct["legs"][0]["platform_prices"], outbound_direct["legs"][0]["cheapest_platform"] = build_platform_price_breakdown(ob_share, is_ob_lcc, rt_direct["airline"])
                    if return_direct.get("legs"):
                        return_direct["legs"][0]["price"] = ret_share
                        is_ret_lcc = return_direct["airline"] in LCC_AIRLINES
                        return_direct["legs"][0]["platform_prices"], return_direct["legs"][0]["cheapest_platform"] = build_platform_price_breakdown(ret_share, is_ret_lcc, return_direct["airline"])
                else:
                    total_rt_direct += return_direct["price"]
            elif return_direct["has_direct_flight"]:
                total_rt_direct += return_direct["price"]

            best_ret_split = return_splits[0]["total_price"] if return_splits else (return_direct["price"] if return_direct["has_direct_flight"] else 0.0)
            total_rt_split += best_ret_split

            combined_60d_avg_direct += return_direct["avg_60d"]
            combined_60d_avg_split += (return_splits[0]["avg_60d"] if return_splits else return_direct["avg_60d"])

        rt_savings = round(total_rt_direct - total_rt_split, 2) if total_rt_direct > 0 else 0.0
        combined_deal_info = evaluate_deal_score(total_rt_split, combined_60d_avg_split, combined_60d_avg_split)

        # High-performance Range Analysis Candidates
        for idx, offset in enumerate(sample_offsets):
            cand_dep = (start_dt + timedelta(days=offset)).strftime("%Y-%m-%d")
            cand_ret = (start_dt + timedelta(days=offset + duration)).strftime("%Y-%m-%d") if is_round_trip else None
            cand_split_price = round(total_rt_split, 2) if total_rt_split > 0 else 0.0
            cand_direct_price = round(total_rt_direct, 2) if total_rt_direct > 0 else 0.0
            cand_savings = round(cand_direct_price - cand_split_price, 2) if cand_direct_price > 0 else 0.0

            if cand_split_price < best_candidate_price:
                best_candidate_price = cand_split_price
                best_candidate_idx = idx

            date_candidates_summary.append({
                "departure_date": cand_dep,
                "return_date": cand_ret,
                "direct_price": cand_direct_price,
                "best_split_price": cand_split_price,
                "best_hub": outbound_splits[0]["hub"]["code"] if outbound_splits else ("DIRECT" if total_rt_direct > 0 else "N/A"),
                "savings": cand_savings,
                "is_cheapest_in_range": False
            })

        if date_candidates_summary:
            date_candidates_summary[best_candidate_idx]["is_cheapest_in_range"] = True
            chosen_candidate = date_candidates_summary[best_candidate_idx]
        else:
            chosen_candidate = {
                "departure_date": outbound_date, "return_date": return_date,
                "best_split_price": total_rt_split, "best_hub": outbound_splits[0]["hub"]["code"] if outbound_splits else "N/A", "savings": rt_savings
            }

        db.commit()

        range_analysis = {
            "range_start": req.range_start or "2026-10-01",
            "range_end": req.range_end or "2026-10-31",
            "trip_duration_days": duration,
            "cheapest_departure_date": chosen_candidate["departure_date"],
            "cheapest_return_date": chosen_candidate.get("return_date") or chosen_candidate["departure_date"],
            "cheapest_package_price": round(chosen_candidate["best_split_price"], 2),
            "cheapest_hub": chosen_candidate["best_hub"],
            "max_range_savings": round(chosen_candidate["savings"], 2),
            "date_candidates": date_candidates_summary
        }

        return {
            "origin": get_airport_info(orig),
            "destination": get_airport_info(dest),
            "target_month": req.range_start[:7] if req.range_start else "2026-10",
            "trip_type": normalized_trip_type,
            "outbound_date": outbound_date,
            "return_date": return_date if is_round_trip else None,
            "direct_option": outbound_direct,
            "split_options": outbound_splits,
            "return_direct_option": return_direct,
            "return_split_options": return_splits,
            "total_round_trip_direct_price": round(total_rt_direct, 2),
            "total_round_trip_best_split_price": round(total_rt_split, 2),
            "round_trip_savings": rt_savings,
            "combined_60d_avg_direct": round(combined_60d_avg_direct, 2),
            "combined_60d_avg_split": round(combined_60d_avg_split, 2),
            "combined_deal_info": combined_deal_info,
            "range_analysis": range_analysis,
            "scraper_status": scraper_status,
            "search_timestamp": datetime.utcnow().isoformat()
        }
    except asyncio.CancelledError:
        print("Search task cancelled cleanly on client disconnect.")
        raise HTTPException(status_code=499, detail="Client Closed Request")

@app.get("/api/deals")
def get_top_deals(db: Session = Depends(get_db)):
    popular_routes = [
        ("BWN", "CTS"), ("BWN", "NRT"), ("BWN", "KUL"),
        ("SIN", "CTS"), ("KUL", "NRT"), ("TPE", "CTS")
    ]
    great_deals = []
    
    for orig, dest in popular_routes:
        stats = calculate_route_statistics(db, orig, dest)
        latest = db.query(PriceHistory).filter(
            PriceHistory.origin == orig,
            PriceHistory.destination == dest
        ).order_by(PriceHistory.scraped_at.desc()).first()

        current_price = latest.price if (latest and latest.price > 0) else 0.0
        
        if current_price > 0 and stats["avg_60d"] > 0:
            deal_info = evaluate_deal_score(current_price, stats["avg_60d"], stats["avg_30d"])

            if deal_info["is_great_deal"]:
                great_deals.append({
                    "origin": orig,
                    "destination": dest,
                    "current_price": round(current_price, 2),
                    "avg_60d": stats["avg_60d"],
                    "avg_30d": stats["avg_30d"],
                    "deal_info": deal_info
                })

    return great_deals
