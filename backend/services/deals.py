from datetime import datetime, timedelta
import random
from typing import Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func
from models import PriceHistory
from services.scraper import generate_realistic_flight_price

def seed_historical_baseline_data(db: Session, origin: str, destination: str, distance_km: float = 1200.0) -> float:
    """
    STRICT NO-FABRICATED DATA: Returns 0.0 if no real historical price records exist in DB.
    Never inserts synthetic baseline rows into SQLite.
    """
    return 0.0

_STATS_CACHE: Dict[Tuple[str, str], Dict[str, Any]] = {}

def calculate_route_statistics(db: Session, origin: str, destination: str, distance_km: float = 1200.0) -> Dict[str, Any]:
    """
    Queries SQLite for 60-day and 30-day moving average pricing.
    Auto-seeds baseline data if history is empty. Uses in-memory caching for speed.
    """
    key = (origin.upper(), destination.upper())
    if key in _STATS_CACHE:
        return _STATS_CACHE[key]

    now = datetime.utcnow()
    cutoff_60d = now - timedelta(days=60)
    cutoff_30d = now - timedelta(days=30)

    # Query 60d records
    prices_60d = db.query(PriceHistory.price).filter(
        PriceHistory.origin == origin,
        PriceHistory.destination == destination,
        PriceHistory.scraped_at >= cutoff_60d
    ).all()

    price_list_60d = [p[0] for p in prices_60d if p[0] > 0]

    if price_list_60d:
        avg_60d = sum(price_list_60d) / len(price_list_60d)
        prices_30d = db.query(PriceHistory.price).filter(
            PriceHistory.origin == origin,
            PriceHistory.destination == destination,
            PriceHistory.scraped_at >= cutoff_30d
        ).all()
        price_list_30d = [p[0] for p in prices_30d if p[0] > 0]
        avg_30d = sum(price_list_30d) / len(price_list_30d) if price_list_30d else avg_60d

        min_price = min(price_list_60d)
        max_price = max(price_list_60d)
    else:
        avg_60d = 0.0
        avg_30d = 0.0
        min_price = 0.0
        max_price = 0.0

    res = {
        "avg_60d": round(avg_60d, 2),
        "avg_30d": round(avg_30d, 2),
        "min_price_60d": round(min_price, 2),
        "max_price_60d": round(max_price, 2),
        "sample_count": len(price_list_60d)
    }
    _STATS_CACHE[key] = res
    return res

def evaluate_deal_score(current_price: float, avg_60d: float, avg_30d: float) -> Dict[str, Any]:
    """
    Evaluates discount percentage against 60-day moving average.
    Flag routes that drop 20%+ below average as "Great Deals".
    Returns tier indicator: green (≥20% off), yellow (5-19% off), red (<5% off).
    """
    discount_pct = round(((avg_60d - current_price) / avg_60d) * 100, 1) if avg_60d > 0 else 0.0

    if discount_pct >= 20.0:
        return {
            "score": "GREAT_DEAL",
            "tier": "green",
            "badge": "🔥 Great Deal",
            "is_great_deal": True,
            "discount_pct": discount_pct,
            "message": f"Price is {discount_pct}% below the 60-day moving average!"
        }
    elif discount_pct >= 5.0:
        return {
            "score": "GOOD_DEAL",
            "tier": "yellow",
            "badge": "⚡ Good Deal",
            "is_great_deal": False,
            "discount_pct": discount_pct,
            "message": f"Price is {discount_pct}% below average."
        }
    else:
        abs_diff = abs(discount_pct)
        return {
            "score": "REGULAR_PRICE",
            "tier": "red",
            "badge": "📊 Standard Rate",
            "is_great_deal": False,
            "discount_pct": discount_pct,
            "message": f"Price is standard or {abs_diff}% above 60-day average."
        }
