# AeroSplit AI Flight Tracker ✈️

> **Intelligent Multi-Hub Flight Routing, Authentic Live Google Flights Scraping & Split-Fare Deal Intelligence**

A full-stack flight monitoring platform designed to uncover cheaper travel routes across Asian transit hubs through intelligent split-ticketing, synchronized multi-leg layovers, and automated background tracking.

---

## ✨ Features

- **Split Route Discovery**: Automatically evaluates direct routes vs. multi-hop connections via Asian transit hubs (KUL, SIN, BKK, HKG, TPE, MNL, ICN, NRT, BKI).
- **Dynamic Multi-Leg Expansion**: Automatically expands flight segments containing intermediate stops/layovers into sequential sub-legs with calculated layovers, transit times, and distance-proportional pricing. No arbitrary leg limits ( \ge 1$).
- **Authentic Google Flights Live Scraping**: Uses Playwright to scrape real live timetables and bundled round-trip fares directly from Google Flights in SGD (S$), preventing isolated one-way price inflation.
- **5-Platform Price Comparison**: Compares prices across Official Airline Direct websites, Trip.com, Google Flights, Agoda, and Booking.com.
- **Automated Daily Background Cron Engine**: Built-in APScheduler runs automated daily price updates with configurable refresh times and manual trigger capabilities.
- **Deal Scoring Intelligence**: Analyzes 30-day and 60-day historical pricing to calculate deal tiers (Great Deal, Good Deal, Regular Fare).
- **Interactive Geospatial Visualization**: Interactive Leaflet maps rendering great-circle curved flight trajectories and airport network nodes.

---

## 🏗️ Architecture

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, SQLite, APScheduler, Playwright (Chromium).
- **Frontend**: Next.js 15+ (App Router), React 19, TypeScript, Tailwind CSS, Leaflet.
- **Deployment**: Docker & Docker Compose support.

---

## 🚀 Getting Started

### 1. Backend Setup

`ash
cd backend
python -m venv venv
.\venv\Scripts\activate      # Windows
# or source venv/bin/activate # Linux / macOS

pip install -r requirements.txt
playwright install chromium

# Seed initial hub & airport data (optional)
python populate_real_routes.py

# Run FastAPI backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
`

The API documentation is accessible at http://localhost:8000/docs.

### 2. Frontend Setup

`ash
cd frontend
npm install
npm run dev
`

Open http://localhost:3000 in your browser.

---

## 🐳 Docker Deployment

`ash
docker-compose up --build -d
`

---

## 📄 License

MIT License.
