import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from database import SessionLocal
from models import PriceHistory, TrackedRoute
from services.graph import build_split_route_options, get_airport_info, has_direct_flight, haversine_distance
from services.scraper import fetch_route_price

import json
import re
from services.deals import calculate_route_statistics, evaluate_deal_score
from services.scraper import (
    fetch_route_price,
    parse_time_to_minutes,
    build_platform_price_breakdown,
    LCC_AIRLINES,
    FLIGHT_SCHEDULE_REGISTRY
)

scheduler = BackgroundScheduler()

# Default daily refresh time (02:00 AM UTC / Configurable)
DEFAULT_DAILY_HOUR = 2
DEFAULT_DAILY_MINUTE = 0
CURRENT_DAILY_TIME = "02:00"
LAST_RUN_TIMESTAMP: Optional[str] = None

def get_segment_distance(code1: str, code2: str) -> float:
    a1 = get_airport_info(code1)
    a2 = get_airport_info(code2)
    return haversine_distance(a1.get("latitude", 0.0), a1.get("longitude", 0.0), a2.get("latitude", 0.0), a2.get("longitude", 0.0))

def parse_duration_to_minutes(dur_str: str) -> int:
    if not dur_str:
        return 0
    h_m = re.search(r"(\d+)\s*(?:hr|h)", str(dur_str), re.IGNORECASE)
    m_m = re.search(r"(\d+)\s*(?:min|m)", str(dur_str), re.IGNORECASE)
    total = 0
    if h_m:
        total += int(h_m.group(1)) * 60
    if m_m:
        total += int(m_m.group(1))
    return total

def format_minutes_to_time(total_mins: int) -> str:
    mins = total_mins % (24 * 60)
    h = mins // 60
    m = mins % 60
    p = "AM" if h < 12 else "PM"
    h12 = h % 12
    if h12 == 0:
        h12 = 12
    days_offset = total_mins // (24 * 60)
    day_str = f"+{days_offset}" if days_offset > 0 else ""
    return f"{h12}:{m:02d} {p}{day_str}"

def expand_leg_with_layovers(leg_dict: dict, origin: str, destination: str) -> list:
    """
    Expands a flight leg into sequential sub-legs if layover stops are detected.
    Calculates sub-leg duration, departure/arrival timestamps, and fair distance-proportional prices.
    Returns list of leg dicts.
    """
    layover_airports = leg_dict.get("layover_airports") or []
    layover_durations = leg_dict.get("layover_durations") or []

    valid_layovers = []
    valid_durations = []
    for idx, a in enumerate(layover_airports):
        if a not in (origin, destination) and a not in valid_layovers:
            valid_layovers.append(a)
            dur = layover_durations[idx] if idx < len(layover_durations) else "Layover"
            valid_durations.append(dur)

    if not valid_layovers:
        return [{
            "origin": origin,
            "destination": destination,
            "airline": leg_dict.get("airline", "Airline"),
            "flight_number": leg_dict.get("flight_number", "N/A"),
            "departure_date": leg_dict.get("departure_date"),
            "departure_time": leg_dict.get("departure_time", "N/A"),
            "arrival_time": leg_dict.get("arrival_time", "N/A"),
            "duration": leg_dict.get("duration", "N/A"),
            "price": round(leg_dict.get("price", 0.0), 2),
            "platform_prices": leg_dict.get("platform_prices", {}),
            "cheapest_platform": leg_dict.get("cheapest_platform", ""),
            "layover_after": None,
        }]

    all_stops = [origin] + valid_layovers + [destination]
    num_segments = len(all_stops) - 1

    distances = []
    for s_idx in range(num_segments):
        d = get_segment_distance(all_stops[s_idx], all_stops[s_idx + 1])
        distances.append(max(d, 100.0))
    total_dist = sum(distances)

    total_dur_mins = parse_duration_to_minutes(leg_dict.get("duration", ""))
    total_layover_mins = sum(parse_duration_to_minutes(ld) for ld in valid_durations)
    flight_time_mins = max(total_dur_mins - total_layover_mins, 60 * num_segments)

    dep_mins = parse_time_to_minutes(leg_dict.get("departure_time")) or 0
    total_price = float(leg_dict.get("price", 0.0))

    expanded = []
    curr_dep_mins = dep_mins
    running_price = 0.0

    for s_idx in range(num_segments):
        s_orig = all_stops[s_idx]
        s_dest = all_stops[s_idx + 1]
        dist_ratio = distances[s_idx] / total_dist if total_dist > 0 else (1.0 / num_segments)

        seg_flight_mins = int(flight_time_mins * dist_ratio)
        seg_arr_mins = curr_dep_mins + seg_flight_mins

        if s_idx == num_segments - 1:
            seg_price = round(max(total_price - running_price, 0.0), 2)
        else:
            seg_price = round(total_price * dist_ratio, 2)
            running_price += seg_price

        dur_str = f"{seg_flight_mins // 60}h {seg_flight_mins % 60:02d}m"

        if s_idx < len(valid_layovers):
            lay_dur_str = valid_durations[s_idx] if s_idx < len(valid_durations) else "Layover"
            lay_mins = parse_duration_to_minutes(lay_dur_str)
            layover_after = {
                "airport": valid_layovers[s_idx],
                "duration": lay_dur_str
            }
            next_dep_mins = seg_arr_mins + lay_mins
        else:
            layover_after = None
            next_dep_mins = seg_arr_mins

        seg_dep_time_str = leg_dict.get("departure_time") if s_idx == 0 else format_minutes_to_time(curr_dep_mins)
        seg_arr_time_str = leg_dict.get("arrival_time") if s_idx == num_segments - 1 else format_minutes_to_time(seg_arr_mins)

        plat_prices = {}
        if leg_dict.get("platform_prices"):
            for plat, plat_p in leg_dict["platform_prices"].items():
                plat_prices[plat] = round(plat_p * dist_ratio, 2) if s_idx < num_segments - 1 else round(plat_p - round(plat_p * (1 - dist_ratio), 2), 2)

        expanded.append({
            "origin": s_orig,
            "destination": s_dest,
            "airline": leg_dict.get("airline", "Airline"),
            "flight_number": leg_dict.get("flight_number", "N/A"),
            "departure_date": leg_dict.get("departure_date"),
            "departure_time": seg_dep_time_str,
            "arrival_time": seg_arr_time_str,
            "duration": dur_str,
            "price": seg_price,
            "platform_prices": plat_prices,
            "cheapest_platform": leg_dict.get("cheapest_platform", ""),
            "layover_after": layover_after
        })

        curr_dep_mins = next_dep_mins

    return expanded

async def refresh_tracked_route_data(r: TrackedRoute, db) -> Dict[str, Any]:
    """
    Performs authentic Playwright live web scraping directly from Google Flights for a tracked route.
    Guarantees:
    - Bundled round-trip scraping for direct round trips (avoiding sum-of-one-ways price inflation).
    - Synchronized layover connections for split transit routes.
    - Candidate date probing across the travel range window.
    - Explicit status: 'available' vs 'no_route_in_range' with diagnostic message.
    - Caching full route schema in r.cached_flight_data and updating r.last_scraped_at.
    - Recording authentic PriceHistory entries in SQLite database.
    """
    orig_info = get_airport_info(r.origin)
    dest_info = get_airport_info(r.destination)
    is_round_trip = (r.trip_type or "round_trip").lower().strip() != "one_way"
    is_ob_direct = has_direct_flight(r.origin, r.destination)
    is_ret_direct = has_direct_flight(r.destination, r.origin) if is_round_trip else False
    is_direct = is_ob_direct and (is_ret_direct if is_round_trip else True)

    duration = r.trip_duration_days or 7
    range_start_str = r.range_start or "2026-10-01"
    range_end_str = r.range_end or "2026-10-31"

    # Compute candidate outbound departure dates within the range
    candidate_dates = [range_start_str]
    try:
        start_d = datetime.strptime(range_start_str, "%Y-%m-%d")
        end_d = datetime.strptime(range_end_str, "%Y-%m-%d")
        span = (end_d - start_d).days
        if span > duration:
            step = max(1, (span - duration) // 2)
            c2 = (start_d + timedelta(days=step)).strftime("%Y-%m-%d")
            if c2 not in candidate_dates:
                candidate_dates.append(c2)
        elif span >= 2:
            candidate_dates.append((start_d + timedelta(days=1)).strftime("%Y-%m-%d"))
    except Exception:
        pass

    splits = build_split_route_options(r.origin, r.destination)
    return_splits = build_split_route_options(r.destination, r.origin) if is_round_trip else []
    best_hub = "DIRECT" if is_direct else (splits[0]["hub"]["code"] if splits else "N/A")

    outbound_legs = []
    return_legs = []
    leg1_detail = None
    leg2_detail = None
    return_leg1_detail = None
    return_leg2_detail = None
    estimated_price = 0.0
    now = datetime.utcnow()
    records = []

    # Probe candidate dates within the travel range
    for outbound_date in candidate_dates:
        cand_records = []
        try:
            cur_start_d = datetime.strptime(outbound_date, "%Y-%m-%d")
            return_date = (cur_start_d + timedelta(days=duration)).strftime("%Y-%m-%d") if is_round_trip else None
        except Exception:
            return_date = range_end_str if is_round_trip else None

        cand_outbound_legs = []
        cand_return_legs = []
        cand_ob_price = 0.0
        cand_ret_price = 0.0
        cand_hub = best_hub

        # 1. OUTBOUND & DIRECT ROUND-TRIP
        if is_ob_direct and is_round_trip and is_ret_direct:
            # Try bundled round-trip direct query
            direct_rt_data = await fetch_route_price(
                r.origin, r.destination, outbound_date,
                return_date=return_date, is_round_trip=True, allow_live_browser=True
            )
            if direct_rt_data.get("is_available") and direct_rt_data.get("price", 0) > 0:
                tot_p = round(direct_rt_data["price"], 2)
                ob_p = round(tot_p / 2, 2)
                ret_p = round(tot_p - ob_p, 2)
                cand_ob_price = ob_p
                cand_ret_price = ret_p
                cand_hub = "DIRECT"

                ob_dict = dict(direct_rt_data)
                ob_dict["price"] = ob_p
                cand_outbound_legs = expand_leg_with_layovers(ob_dict, r.origin, r.destination)

                # Return timetable scrape
                ret_sched = await fetch_route_price(r.destination, r.origin, return_date, allow_live_browser=True)
                if ret_sched.get("is_available") and ret_sched.get("price", 0) > 0:
                    ret_dict = dict(ret_sched)
                    ret_dict["price"] = ret_p
                    cand_return_legs = expand_leg_with_layovers(ret_dict, r.destination, r.origin)
                else:
                    is_ob_lcc = direct_rt_data["airline"] in LCC_AIRLINES
                    ret_plat, ret_c = build_platform_price_breakdown(ret_p, is_ob_lcc, direct_rt_data["airline"])
                    ret_dep_t = direct_rt_data.get("departure_time", "N/A")
                    ret_arr_t = direct_rt_data.get("arrival_time", "N/A")
                    ret_dur = direct_rt_data.get("duration", "N/A")
                    ret_air = direct_rt_data["airline"]
                    if (r.destination, r.origin) in FLIGHT_SCHEDULE_REGISTRY:
                        sc = FLIGHT_SCHEDULE_REGISTRY[(r.destination, r.origin)][0]
                        ret_air = sc["airline"]
                        ret_dep_t = sc["departure_time"]
                        ret_arr_t = sc["arrival_time"]
                        ret_dur = sc["duration"]

                    cand_return_legs = [{
                        "origin": r.destination, "destination": r.origin,
                        "airline": ret_air, "flight_number": direct_rt_data.get("flight_number", "N/A"),
                        "departure_date": return_date,
                        "departure_time": ret_dep_t, "arrival_time": ret_arr_t,
                        "duration": ret_dur, "price": ret_p,
                        "platform_prices": ret_plat, "cheapest_platform": ret_c,
                        "layover_after": None,
                    }]

                cand_records.append(PriceHistory(
                    origin=r.origin, destination=r.destination,
                    airline=direct_rt_data["airline"], flight_number=direct_rt_data.get("flight_number", "N/A"),
                    departure_date=outbound_date, price=tot_p,
                    currency="SGD", is_direct=True, scraped_at=now
                ))

        elif is_ob_direct:
            ob_data = await fetch_route_price(r.origin, r.destination, outbound_date, allow_live_browser=True)
            if ob_data.get("is_available") and ob_data.get("price", 0) > 0:
                cand_ob_price = round(ob_data["price"], 2)
                cand_outbound_legs = expand_leg_with_layovers(ob_data, r.origin, r.destination)
                cand_records.append(PriceHistory(
                    origin=r.origin, destination=r.destination,
                    airline=ob_data["airline"], flight_number=ob_data.get("flight_number", "N/A"),
                    departure_date=outbound_date, price=cand_ob_price,
                    currency="SGD", is_direct=True, scraped_at=now
                ))

        # 2. SPLIT OUTBOUND (if direct outbound not found or not direct)
        if cand_ob_price == 0 and splits:
            for split in splits[:3]:
                h_code = split["hub"]["code"]
                l1_data = await fetch_route_price(r.origin, h_code, outbound_date, split["leg1"]["distance_km"], allow_live_browser=True)
                if not l1_data.get("is_available") or l1_data.get("price", 0) <= 0:
                    continue
                l1_arr_mins = parse_time_to_minutes(l1_data.get("arrival_time"))
                min_dep_2 = (l1_arr_mins + 45) if l1_arr_mins is not None else None

                l2_data = await fetch_route_price(h_code, r.destination, outbound_date, split["leg2"]["distance_km"], allow_live_browser=True, min_dep_minutes=min_dep_2)
                if not l2_data.get("is_available") or l2_data.get("price", 0) <= 0:
                    if l1_arr_mins and l1_arr_mins >= 1200:
                        next_dep = (datetime.strptime(outbound_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
                        l2_data = await fetch_route_price(h_code, r.destination, next_dep, split["leg2"]["distance_km"], allow_live_browser=True)

                if l1_data.get("is_available") and l2_data.get("is_available") and l2_data.get("price", 0) > 0:
                    cand_ob_price = round(l1_data["price"] + l2_data["price"], 2)
                    cand_hub = h_code
                    l1_expanded = expand_leg_with_layovers(l1_data, r.origin, h_code)
                    l2_expanded = expand_leg_with_layovers(l2_data, h_code, r.destination)

                    # Calculate transit layover between l1 and l2 at h_code
                    l1_arr = parse_time_to_minutes(l1_expanded[-1].get("arrival_time"))
                    l2_dep = parse_time_to_minutes(l2_expanded[0].get("departure_time"))
                    transit_mins = 0
                    if l1_arr is not None and l2_dep is not None:
                        if l2_dep >= l1_arr:
                            transit_mins = l2_dep - l1_arr
                        else:
                            transit_mins = (24 * 60 - l1_arr) + l2_dep
                    if transit_mins > 0:
                        t_str = f"{transit_mins // 60}h {transit_mins % 60:02d}m" if transit_mins >= 60 else f"{transit_mins}m"
                        l1_expanded[-1]["layover_after"] = {"airport": h_code, "duration": t_str}
                    else:
                        l1_expanded[-1]["layover_after"] = {"airport": h_code, "duration": "Transit"}

                    cand_outbound_legs = l1_expanded + l2_expanded

                    cand_records.append(PriceHistory(
                        origin=r.origin, destination=h_code,
                        airline=l1_data["airline"], flight_number=l1_data.get("flight_number", "N/A"),
                        departure_date=outbound_date, price=l1_data["price"],
                        currency="SGD", is_direct=True, scraped_at=now
                    ))
                    cand_records.append(PriceHistory(
                        origin=h_code, destination=r.destination,
                        airline=l2_data["airline"], flight_number=l2_data.get("flight_number", "N/A"),
                        departure_date=outbound_date, price=l2_data["price"],
                        currency="SGD", is_direct=True, scraped_at=now
                    ))
                    break

        # 3. RETURN JOURNEY (if round trip and return leg not already set by direct bundled scrape)
        if is_round_trip and not cand_return_legs:
            # Check direct return first if destination -> origin has direct operating flight
            if is_ret_direct:
                ret_dir = await fetch_route_price(r.destination, r.origin, return_date, allow_live_browser=True)
                if ret_dir.get("is_available") and ret_dir.get("price", 0) > 0:
                    cand_ret_price = round(ret_dir["price"], 2)
                    cand_return_legs = expand_leg_with_layovers(ret_dir, r.destination, r.origin)
                    cand_records.append(PriceHistory(
                        origin=r.destination, destination=r.origin,
                        airline=ret_dir["airline"], flight_number=ret_dir.get("flight_number", "N/A"),
                        departure_date=return_date, price=cand_ret_price,
                        currency="SGD", is_direct=True, scraped_at=now
                    ))

            # If return not direct or direct return unavailable, check return split options
            if cand_ret_price == 0 and return_splits:
                ordered_ret = []
                if cand_hub and cand_hub != "DIRECT" and cand_hub != "N/A":
                    ordered_ret = [s for s in return_splits if s["hub"]["code"] == cand_hub] + [s for s in return_splits if s["hub"]["code"] != cand_hub]
                else:
                    ordered_ret = return_splits

                for ret_split in ordered_ret[:4]:
                    ret_h_code = ret_split["hub"]["code"]
                    rl1_data = await fetch_route_price(r.destination, ret_h_code, return_date, ret_split["leg1"]["distance_km"], allow_live_browser=True)
                    if not rl1_data.get("is_available") or rl1_data.get("price", 0) <= 0:
                        continue
                    rl1_arr_mins = parse_time_to_minutes(rl1_data.get("arrival_time"))
                    min_ret_dep_2 = (rl1_arr_mins + 45) if rl1_arr_mins is not None else None

                    rl2_data = await fetch_route_price(ret_h_code, r.origin, return_date, ret_split["leg2"]["distance_km"], allow_live_browser=True, min_dep_minutes=min_ret_dep_2)
                    if not rl2_data.get("is_available") or rl2_data.get("price", 0) <= 0:
                        if rl1_arr_mins and rl1_arr_mins >= 1200:
                            next_ret_d = (datetime.strptime(return_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
                            rl2_data = await fetch_route_price(ret_h_code, r.origin, next_ret_d, ret_split["leg2"]["distance_km"], allow_live_browser=True)

                    if rl1_data.get("is_available") and rl2_data.get("is_available") and rl2_data.get("price", 0) > 0:
                        cand_ret_price = round(rl1_data["price"] + rl2_data["price"], 2)
                        rl1_expanded = expand_leg_with_layovers(rl1_data, r.destination, ret_h_code)
                        rl2_expanded = expand_leg_with_layovers(rl2_data, ret_h_code, r.origin)

                        rl1_arr = parse_time_to_minutes(rl1_expanded[-1].get("arrival_time"))
                        rl2_dep = parse_time_to_minutes(rl2_expanded[0].get("departure_time"))
                        r_transit_mins = 0
                        if rl1_arr is not None and rl2_dep is not None:
                            if rl2_dep >= rl1_arr:
                                r_transit_mins = rl2_dep - rl1_arr
                            else:
                                r_transit_mins = (24 * 60 - rl1_arr) + rl2_dep
                        if r_transit_mins > 0:
                            rt_str = f"{r_transit_mins // 60}h {r_transit_mins % 60:02d}m" if r_transit_mins >= 60 else f"{r_transit_mins}m"
                            rl1_expanded[-1]["layover_after"] = {"airport": ret_h_code, "duration": rt_str}
                        else:
                            rl1_expanded[-1]["layover_after"] = {"airport": ret_h_code, "duration": "Transit"}

                        cand_return_legs = rl1_expanded + rl2_expanded

                        cand_records.append(PriceHistory(
                            origin=r.destination, destination=ret_h_code,
                            airline=rl1_data["airline"], flight_number=rl1_data.get("flight_number", "N/A"),
                            departure_date=return_date, price=rl1_data["price"],
                            currency="SGD", is_direct=True, scraped_at=now
                        ))
                        cand_records.append(PriceHistory(
                            origin=ret_h_code, destination=r.origin,
                            airline=rl2_data["airline"], flight_number=rl2_data.get("flight_number", "N/A"),
                            departure_date=return_date, price=rl2_data["price"],
                            currency="SGD", is_direct=True, scraped_at=now
                        ))
                        break

        # 4. TRIP COMPLETION VERIFICATION
        if is_round_trip:
            if cand_ob_price > 0 and cand_ret_price > 0 and len(cand_outbound_legs) > 0 and len(cand_return_legs) > 0:
                outbound_legs = cand_outbound_legs
                return_legs = cand_return_legs
                best_hub = cand_hub
                estimated_price = round(cand_ob_price + cand_ret_price, 2)
                records = cand_records
                break
        else:
            if cand_ob_price > 0 and len(cand_outbound_legs) > 0:
                outbound_legs = cand_outbound_legs
                return_legs = []
                best_hub = cand_hub
                estimated_price = round(cand_ob_price, 2)
                records = cand_records
                break

    # Determine status & diagnostic message
    if is_round_trip:
        is_complete = estimated_price > 0 and len(outbound_legs) > 0 and len(return_legs) > 0
    else:
        is_complete = estimated_price > 0 and len(outbound_legs) > 0

    if is_complete:
        status = "available"
        dep_date_used = outbound_legs[0].get("departure_date", range_start_str) if outbound_legs else range_start_str
        ret_date_used = return_legs[0].get("departure_date", range_end_str) if return_legs else range_end_str
        if is_round_trip:
            status_message = f"Live round-trip flight verified: Outbound {dep_date_used}, Return {ret_date_used}."
        else:
            status_message = f"Live one-way flight verified departing {dep_date_used}."
    else:
        status = "no_route_in_range"
        estimated_price = 0.0
        outbound_legs = []
        return_legs = []
        if is_round_trip:
            status_message = f"No complete round-trip flight route could be found for {r.origin} ⇄ {r.destination} within the specified travel range ({range_start_str} to {range_end_str}, duration {duration} days)."
        else:
            status_message = f"No operating flight route found for {r.origin} ➔ {r.destination} within the specified travel range ({range_start_str} to {range_end_str})."

    # Compute human-readable hub string showing all transit points
    if outbound_legs:
        transit_stops = []
        for l in outbound_legs[:-1]:
            if l["destination"] not in transit_stops and l["destination"] != r.destination:
                transit_stops.append(l["destination"])
        if transit_stops:
            best_hub = ", ".join(transit_stops)
        elif is_direct:
            best_hub = "DIRECT"
        else:
            best_hub = cand_hub or "N/A"

    # Legacy 2-leg compatibility pointers
    leg1_detail = outbound_legs[0] if len(outbound_legs) > 0 else None
    leg2_detail = outbound_legs[1] if len(outbound_legs) > 1 else None
    return_leg1_detail = return_legs[0] if len(return_legs) > 0 else None
    return_leg2_detail = return_legs[1] if len(return_legs) > 1 else None

    stats = calculate_route_statistics(db, r.origin, r.destination)
    deal_info = evaluate_deal_score(estimated_price, stats["avg_60d"], stats["avg_30d"])

    route_dict = {
        "id": r.id,
        "origin": orig_info,
        "destination": dest_info,
        "range_start": r.range_start,
        "range_end": r.range_end,
        "trip_duration_days": r.trip_duration_days,
        "trip_type": r.trip_type,
        "has_direct_flight": is_direct,
        "best_hub": best_hub,
        "estimated_price": estimated_price,
        "avg_60d": stats["avg_60d"],
        "deal_info": deal_info,
        "outbound_legs": outbound_legs,
        "return_legs": return_legs,
        "leg1": leg1_detail,
        "leg2": leg2_detail,
        "return_leg1": return_leg1_detail,
        "return_leg2": return_leg2_detail,
        "status": status,
        "status_message": status_message,
        "is_active": r.is_active,
        "created_at": r.created_at.isoformat() if r.created_at else datetime.utcnow().isoformat()
    }

    # Always persist in cache so subsequent page visits do not re-scrape and render instantly
    r.cached_flight_data = json.dumps(route_dict)
    r.last_scraped_at = now
    if records:
        db.bulk_save_objects(records)
    db.commit()

    return route_dict

async def async_daily_tracked_routes_scraper_job() -> Dict[str, Any]:
    """
    Async implementation of daily background scraper job.
    Scrapes and updates authentic price history records and cached flight data for all active tracked routes.
    """
    global LAST_RUN_TIMESTAMP
    db = SessionLocal()
    refreshed_routes = []

    try:
        now = datetime.utcnow()
        LAST_RUN_TIMESTAMP = now.isoformat()
        
        active_routes = db.query(TrackedRoute).filter(TrackedRoute.is_active == True).all()
        for r in active_routes:
            try:
                res = await refresh_tracked_route_data(r, db)
                refreshed_routes.append(res)
            except Exception as route_err:
                print(f"Error refreshing route {r.id} ({r.origin}->{r.destination}): {route_err}")

        print(f"[{now.isoformat()}] APScheduler Daily Cron: Refreshed authentic price data for {len(refreshed_routes)} tracked routes.")
        return {
            "routes_count": len(refreshed_routes),
            "timestamp": LAST_RUN_TIMESTAMP,
            "routes": [{"id": r["id"], "origin": r["origin"]["code"], "destination": r["destination"]["code"], "price": r["estimated_price"]} for r in refreshed_routes]
        }
    except Exception as e:
        print(f"APScheduler daily job error: {e}")
        return {
            "routes_count": len(refreshed_routes),
            "error": str(e),
            "timestamp": LAST_RUN_TIMESTAMP
        }
    finally:
        db.close()

def daily_tracked_routes_scraper_job():
    """Sync wrapper for APScheduler background cron execution."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(async_daily_tracked_routes_scraper_job())
        else:
            loop.run_until_complete(async_daily_tracked_routes_scraper_job())
    except Exception:
        asyncio.run(async_daily_tracked_routes_scraper_job())

def configure_daily_schedule(time_str: str = "02:00"):
    """
    Configures the daily cron schedule at a specific time string "HH:MM".
    """
    global CURRENT_DAILY_TIME, DEFAULT_DAILY_HOUR, DEFAULT_DAILY_MINUTE
    try:
        parts = time_str.strip().split(":")
        hour = int(parts[0]) % 24
        minute = int(parts[1]) % 60
        
        DEFAULT_DAILY_HOUR = hour
        DEFAULT_DAILY_MINUTE = minute
        CURRENT_DAILY_TIME = f"{hour:02d}:{minute:02d}"

        if scheduler.running:
            scheduler.add_job(
                daily_tracked_routes_scraper_job,
                CronTrigger(hour=hour, minute=minute),
                id='daily_flight_scraper_cron',
                replace_existing=True
            )
            print(f"APScheduler daily cron updated to trigger at {CURRENT_DAILY_TIME} UTC.")
    except Exception as e:
        print(f"Configure daily schedule error: {e}")

def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            daily_tracked_routes_scraper_job,
            CronTrigger(hour=DEFAULT_DAILY_HOUR, minute=DEFAULT_DAILY_MINUTE),
            id='daily_flight_scraper_cron',
            replace_existing=True
        )
        scheduler.start()
        print(f"APScheduler daily background flight tracker started (Daily Cron at {CURRENT_DAILY_TIME} UTC).")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("APScheduler stopped.")

def get_scheduler_status() -> Dict[str, Any]:
    db = SessionLocal()
    try:
        active_count = db.query(TrackedRoute).filter(TrackedRoute.is_active == True).count()
    finally:
        db.close()

    job = scheduler.get_job('daily_flight_scraper_cron') if scheduler.running else None
    next_run = job.next_run_time.isoformat() if job and job.next_run_time else None

    return {
        "status": "running" if scheduler.running else "stopped",
        "schedule_type": "daily_cron",
        "daily_time": CURRENT_DAILY_TIME,
        "cron_expression": f"{DEFAULT_DAILY_MINUTE} {DEFAULT_DAILY_HOUR} * * * (Daily at {CURRENT_DAILY_TIME} UTC)",
        "next_run_at": next_run,
        "last_run_at": LAST_RUN_TIMESTAMP,
        "tracked_routes_count": active_count
    }
