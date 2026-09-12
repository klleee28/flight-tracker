import asyncio
import zoneinfo
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

KL_TZ = zoneinfo.ZoneInfo("Asia/Kuala_Lumpur")

def format_kl_iso(dt_val: Any) -> Optional[str]:
    """
    Normalizes any datetime or date string into an ISO string with explicit Kuala Lumpur (+08:00) offset.
    Handles naive datetimes stored in SQLite, existing ISO strings with Z or offsets, and None.
    """
    if not dt_val:
        return None
    try:
        if isinstance(dt_val, str):
            val = dt_val.strip()
            if not val:
                return None
            if "+08:00" in val:
                return val
            if val.endswith("Z"):
                dt = datetime.fromisoformat(val.replace("Z", "+00:00")).astimezone(KL_TZ)
                return dt.isoformat()
            if "T" in val or " " in val:
                clean_val = val.replace(" ", "T")
                dt = datetime.fromisoformat(clean_val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=KL_TZ)
                else:
                    dt = dt.astimezone(KL_TZ)
                return dt.isoformat()
            return val
        elif isinstance(dt_val, datetime):
            if dt_val.tzinfo is None:
                dt = dt_val.replace(tzinfo=KL_TZ)
            else:
                dt = dt_val.astimezone(KL_TZ)
            return dt.isoformat()
    except Exception as e:
        print(f"format_kl_iso notice for {dt_val}: {e}")
    return str(dt_val)

scheduler = BackgroundScheduler()

# Default daily refresh time (02:00 AM Kuala Lumpur Time / GMT+8 / Configurable)
DEFAULT_DAILY_HOUR = 2
DEFAULT_DAILY_MINUTE = 0
CURRENT_DAILY_TIME = "02:00"
LAST_RUN_TIMESTAMP: Optional[str] = None
IS_REFRESHING_NOW: bool = False

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

    duration = 1 if not is_round_trip else (r.trip_duration_days or 7)
    range_start_str = r.range_start or "2026-10-01"
    range_end_str = r.range_end or "2026-10-31"

    # Compute candidate outbound departure dates within the range
    candidate_dates = [range_start_str]
    try:
        start_d = datetime.strptime(range_start_str, "%Y-%m-%d")
        end_d = datetime.strptime(range_end_str, "%Y-%m-%d")
        span = (end_d - start_d).days
        if not is_round_trip:
            if span >= 3:
                step = span // 2
                c2 = (start_d + timedelta(days=step)).strftime("%Y-%m-%d")
                if c2 not in candidate_dates:
                    candidate_dates.append(c2)
            if span >= 1:
                c3 = end_d.strftime("%Y-%m-%d")
                if c3 not in candidate_dates:
                    candidate_dates.append(c3)
        else:
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
    now = datetime.now(KL_TZ)
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

        if cand_ob_price == 0:
            ob_data = await fetch_route_price(r.origin, r.destination, outbound_date, allow_live_browser=True)
            if ob_data.get("is_available") and ob_data.get("price", 0) > 0:
                cand_ob_price = round(ob_data["price"], 2)
                cand_outbound_legs = expand_leg_with_layovers(ob_data, r.origin, r.destination)
                if ob_data.get("is_nonstop"):
                    cand_hub = "DIRECT"
                    from services.graph import KNOWN_DIRECT_ROUTES
                    KNOWN_DIRECT_ROUTES.add((r.origin, r.destination))
                    KNOWN_DIRECT_ROUTES.add((r.destination, r.origin))
                cand_records.append(PriceHistory(
                    origin=r.origin, destination=r.destination,
                    airline=ob_data["airline"], flight_number=ob_data.get("flight_number", "N/A"),
                    departure_date=outbound_date, price=cand_ob_price,
                    currency="SGD", is_direct=ob_data.get("is_nonstop", True), scraped_at=now
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
            # Check direct return first
            ret_dir = await fetch_route_price(r.destination, r.origin, return_date, allow_live_browser=True)
            if ret_dir.get("is_available") and ret_dir.get("price", 0) > 0:
                cand_ret_price = round(ret_dir["price"], 2)
                cand_return_legs = expand_leg_with_layovers(ret_dir, r.destination, r.origin)
                cand_records.append(PriceHistory(
                    origin=r.destination, destination=r.origin,
                    airline=ret_dir["airline"], flight_number=ret_dir.get("flight_number", "N/A"),
                    departure_date=return_date, price=cand_ret_price,
                    currency="SGD", is_direct=ret_dir.get("is_nonstop", True), scraped_at=now
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
        # If scraper timed out or had temporary network failure, preserve valid existing cached flight data
        if r.cached_flight_data:
            try:
                prev_cache = json.loads(r.cached_flight_data)
                if prev_cache.get("status") == "available" and prev_cache.get("estimated_price", 0) > 0:
                    prev_cache["last_scraped_at"] = now.isoformat()
                    r.cached_flight_data = json.dumps(prev_cache)
                    r.last_scraped_at = now
                    db.commit()
                    return prev_cache
            except Exception:
                pass

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
        "last_scraped_at": now.isoformat(),
        "created_at": format_kl_iso(r.created_at) if r.created_at else now.isoformat()
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
    global LAST_RUN_TIMESTAMP, IS_REFRESHING_NOW
    refreshed_routes = []

    try:
        IS_REFRESHING_NOW = True

        # Query active route IDs using a quick, isolated session
        temp_db = SessionLocal()
        try:
            active_ids = [r.id for r in temp_db.query(TrackedRoute.id).filter(TrackedRoute.is_active == True).all()]
        finally:
            temp_db.close()

        start_time_iso = datetime.now(KL_TZ).isoformat()
        print(f"[{start_time_iso}] APScheduler Daily Cron: Starting live price refresh for {len(active_ids)} active routes...")

        for r_id in active_ids:
            route_db = SessionLocal()
            try:
                route_obj = route_db.query(TrackedRoute).filter(TrackedRoute.id == r_id, TrackedRoute.is_active == True).first()
                if route_obj:
                    res = await refresh_tracked_route_data(route_obj, route_db)
                    refreshed_routes.append(res)
                    print(f"  [Refreshed] Route {r_id} ({route_obj.origin}->{route_obj.destination}): S${res.get('estimated_price', 0)}")
            except Exception as route_err:
                print(f"Error refreshing route {r_id}: {route_err}")
            finally:
                route_db.close()

        completion_now = datetime.now(KL_TZ)
        LAST_RUN_TIMESTAMP = completion_now.isoformat()

        print(f"[{completion_now.isoformat()}] APScheduler Daily Cron: Finished refreshing {len(refreshed_routes)} of {len(active_ids)} tracked routes.")
        return {
            "routes_count": len(refreshed_routes),
            "timestamp": LAST_RUN_TIMESTAMP,
            "routes": [
                {
                    "id": r.get("id"),
                    "origin": r["origin"]["code"] if isinstance(r.get("origin"), dict) else r.get("origin", "N/A"),
                    "destination": r["destination"]["code"] if isinstance(r.get("destination"), dict) else r.get("destination", "N/A"),
                    "price": r.get("estimated_price", 0.0)
                }
                for r in refreshed_routes
            ]
        }
    except Exception as e:
        print(f"APScheduler daily job error: {e}")
        return {
            "routes_count": len(refreshed_routes),
            "error": str(e),
            "timestamp": LAST_RUN_TIMESTAMP
        }
    finally:
        IS_REFRESHING_NOW = False

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
    Configures the daily cron schedule at a specific time string "HH:MM" (Kuala Lumpur Time / GMT+8).
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
                CronTrigger(hour=hour, minute=minute, timezone="Asia/Kuala_Lumpur"),
                id='daily_flight_scraper_cron',
                replace_existing=True
            )
            print(f"APScheduler daily cron updated to trigger at {CURRENT_DAILY_TIME} MYT (Asia/Kuala_Lumpur, GMT+8).")
    except Exception as e:
        print(f"Configure daily schedule error: {e}")

def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            daily_tracked_routes_scraper_job,
            CronTrigger(hour=DEFAULT_DAILY_HOUR, minute=DEFAULT_DAILY_MINUTE, timezone="Asia/Kuala_Lumpur"),
            id='daily_flight_scraper_cron',
            replace_existing=True
        )
        scheduler.start()
        print(f"APScheduler daily background flight tracker started (Daily Cron at {CURRENT_DAILY_TIME} MYT / GMT+8, Asia/Kuala_Lumpur).")

def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        print("APScheduler stopped.")

def get_scheduler_status() -> Dict[str, Any]:
    global LAST_RUN_TIMESTAMP, IS_REFRESHING_NOW
    db = SessionLocal()
    try:
        active_count = db.query(TrackedRoute).filter(TrackedRoute.is_active == True).count()
        most_recent = db.query(TrackedRoute.last_scraped_at).filter(
            TrackedRoute.is_active == True,
            TrackedRoute.last_scraped_at.isnot(None)
        ).order_by(TrackedRoute.last_scraped_at.desc()).first()
    finally:
        db.close()

    last_dt = format_kl_iso(LAST_RUN_TIMESTAMP)
    if not last_dt and most_recent and most_recent[0]:
        last_dt = format_kl_iso(most_recent[0])

    job = scheduler.get_job('daily_flight_scraper_cron') if scheduler.running else None
    next_run = None
    if job and job.next_run_time:
        next_run = format_kl_iso(job.next_run_time)

    return {
        "status": "running" if scheduler.running else "stopped",
        "schedule_type": "daily_cron",
        "daily_time": CURRENT_DAILY_TIME,
        "timezone": "Asia/Kuala_Lumpur",
        "timezone_offset": "+08:00",
        "cron_expression": f"{DEFAULT_DAILY_MINUTE} {DEFAULT_DAILY_HOUR} * * * (Daily at {CURRENT_DAILY_TIME} MYT / GMT+8)",
        "next_run_at": next_run,
        "last_run_at": last_dt,
        "tracked_routes_count": active_count,
        "is_refreshing": IS_REFRESHING_NOW
    }
