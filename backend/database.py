import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DB_FILE = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(__file__), "flight_tracker.db"))
db_dir = os.path.dirname(DB_FILE)
if db_dir and not os.path.exists(db_dir):
    os.makedirs(db_dir, exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_FILE}"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

from sqlalchemy import text

def ensure_db_migrations():
    """
    Safely executes non-destructive schema migrations for existing SQLite databases.
    """
    try:
        with engine.connect() as conn:
            # Check tracked_routes columns
            res = conn.execute(text("PRAGMA table_info(tracked_routes)")).fetchall()
            cols = [r[1] for r in res]
            if cols and "title" not in cols:
                conn.execute(text("ALTER TABLE tracked_routes ADD COLUMN title VARCHAR(100)"))
                conn.commit()
                print("[Migration] Added 'title' column to tracked_routes table.")
    except Exception as e:
        print(f"[Migration notice] {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
