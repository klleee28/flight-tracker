from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Hub(Base):
    __tablename__ = "hubs"

    code = Column(String(5), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)

class Route(Base):
    __tablename__ = "routes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    origin = Column(String(5), nullable=False, index=True)
    destination = Column(String(5), nullable=False, index=True)
    is_hub_connection = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class TrackedRoute(Base):
    __tablename__ = "tracked_routes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    origin = Column(String(5), nullable=False, index=True)
    destination = Column(String(5), nullable=False, index=True)
    range_start = Column(String(20), nullable=False, default="2026-10-01")
    range_end = Column(String(20), nullable=False, default="2026-10-31")
    trip_duration_days = Column(Integer, default=10)
    trip_type = Column(String(20), default="round_trip")
    cached_flight_data = Column(String, nullable=True)
    last_scraped_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    origin = Column(String(5), nullable=False, index=True)
    destination = Column(String(5), nullable=False, index=True)
    airline = Column(String(100), nullable=False)
    flight_number = Column(String(50), nullable=True)
    departure_date = Column(String(20), nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(String(10), default="SGD")
    is_direct = Column(Boolean, default=True)
    scraped_at = Column(DateTime, default=datetime.utcnow, index=True)
