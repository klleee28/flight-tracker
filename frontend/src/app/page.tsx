"use client";

import React, { useState, useEffect, useRef } from "react";
import FlightSearchForm from "@/components/FlightSearchForm";
import RouteComparisonMatrix from "@/components/RouteComparisonMatrix";
import HubGraphVisualizer from "@/components/HubGraphVisualizer";
import TrackedRoutesList, { ScheduleStatus } from "@/components/TrackedRoutesList";
import { SearchResponse, GreatDealItem, TrackedRouteItem } from "@/types/flight";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [mounted, setMounted] = useState(false);
  const [searchResult, setSearchResult] = useState<SearchResponse | null>(null);
  const [greatDeals, setGreatDeals] = useState<GreatDealItem[]>([]);
  const [trackedRoutes, setTrackedRoutes] = useState<TrackedRouteItem[]>([]);
  const [scheduleStatus, setScheduleStatus] = useState<ScheduleStatus | null>(null);
  const [selectedHub, setSelectedHub] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  // Initial load fetches deals, active tracked routes, and schedule status
  useEffect(() => {
    setMounted(true);
    fetchGreatDeals();
    fetchTrackedRoutes();
    fetchScheduleStatus();
  }, []);

  const fetchGreatDeals = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/deals`);
      if (res.ok) {
        const deals = await res.json();
        setGreatDeals(deals);
      }
    } catch (err) {
      console.log("Deals fetch notice:", err);
    }
  };

  const fetchTrackedRoutes = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/tracked-routes`);
      if (res.ok) {
        const routes = await res.json();
        setTrackedRoutes(routes);
      }
    } catch (err) {
      console.log("Tracked routes fetch notice:", err);
    }
  };

  const fetchScheduleStatus = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/scheduler/status`);
      if (res.ok) {
        const status = await res.json();
        setScheduleStatus(status);
      }
    } catch (err) {
      console.log("Scheduler status fetch notice:", err);
    }
  };

  const handleSearch = async (
    origin: string,
    destination: string,
    rangeStart: string = "2026-10-01",
    rangeEnd: string = "2026-10-31",
    tripDuration: number = 10,
    tripType: string = "round_trip"
  ) => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    const controller = new AbortController();
    abortControllerRef.current = controller;

    setIsLoading(true);
    setErrorMsg(null);
    setSelectedHub(null);

    try {
      const res = await fetch(`${API_BASE_URL}/api/flights/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        signal: controller.signal,
        body: JSON.stringify({
          origin,
          destination,
          range_start: rangeStart,
          range_end: rangeEnd,
          trip_duration_days: tripDuration,
          trip_type: tripType,
        }),
      });

      if (!res.ok) {
        throw new Error(`API error: ${res.statusText}`);
      }

      const data: SearchResponse = await res.json();
      setSearchResult(data);
    } catch (err: any) {
      if (err.name === "AbortError") {
        console.log("Flight search aborted by user.");
        setErrorMsg("Search stopped by user.");
      } else {
        console.error("Flight search error:", err);
        setErrorMsg(err.message || "Failed to fetch split-route flight comparison.");
      }
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
        setIsLoading(false);
      }
    }
  };

  const handleStopSearch = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
  };

  const handleAddTrackedRoute = async (
    origin: string,
    destination: string,
    rangeStart: string,
    rangeEnd: string,
    tripDuration: number,
    tripType: string
  ): Promise<any> => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/tracked-routes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          origin,
          destination,
          range_start: rangeStart,
          range_end: rangeEnd,
          trip_duration_days: tripDuration,
          trip_type: tripType,
        }),
      });
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Failed to add tracked route.");
      }
      const data = await res.json();
      await fetchTrackedRoutes();
      await fetchScheduleStatus();
      return data;
    } catch (err) {
      console.error("Add tracked route error:", err);
      throw err;
    }
  };

  const handleDeleteTrackedRoute = async (id: number) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/tracked-routes/${id}`, {
        method: "DELETE",
      });
      if (res.ok) {
        await fetchTrackedRoutes();
        await fetchScheduleStatus();
      }
    } catch (err) {
      console.error("Delete tracked route error:", err);
    }
  };

  const handleTriggerDailyRefreshNow = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/scheduler/trigger-now`, {
        method: "POST",
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || errData.message || `Server error (${res.status}): ${res.statusText}`);
      }
      await Promise.all([
        fetchTrackedRoutes(),
        fetchGreatDeals(),
        fetchScheduleStatus(),
      ]);
    } catch (err: any) {
      console.error("Trigger daily refresh error:", err);
      throw err;
    }
  };

  const handleChangeDailyTime = async (dailyTimeStr: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/scheduler/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ daily_time: dailyTimeStr }),
      });
      if (res.ok) {
        await fetchScheduleStatus();
      }
    } catch (err) {
      console.error("Change daily time error:", err);
    }
  };

  const activeHubCode = selectedHub || searchResult?.split_options?.[0]?.hub?.code || "KUL";

  if (!mounted) {
    return <main className="min-h-screen bg-slate-950 text-slate-100" />;
  }

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 font-sans antialiased selection:bg-cyan-500 selection:text-slate-950">
      {/* Background glow effects */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute -top-40 -left-40 w-96 h-96 bg-cyan-600/15 rounded-full blur-3xl" />
        <div className="absolute top-1/3 -right-40 w-96 h-96 bg-indigo-600/15 rounded-full blur-3xl" />
        <div className="absolute bottom-10 left-1/3 w-96 h-96 bg-emerald-600/10 rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Navigation Header */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-indigo-600 flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-cyan-500/20">
              ✈️
            </div>
            <div>
              <h1 className="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
                AERO<span className="text-cyan-400">SPLIT</span> AI
              </h1>
              <p className="text-xs text-slate-400">
                Automated Asian Transit Hub Routing &amp; 60-Day Deal Intelligence
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-bold ${
              searchResult?.scraper_status?.is_live
                ? "bg-emerald-950/80 border-emerald-500/50 text-emerald-300"
                : "bg-amber-950/80 border-amber-500/50 text-amber-300"
            }`}>
              <span className={`w-2 h-2 rounded-full ${searchResult?.scraper_status?.is_live ? "bg-emerald-400 animate-pulse" : "bg-amber-400"}`} />
              <span>{searchResult?.scraper_status?.status_badge || "⚡ Engine Ready"}</span>
            </div>
            <div className="px-3 py-1.5 rounded-full bg-cyan-950/60 border border-cyan-500/30 text-cyan-300 text-xs font-semibold">
              Global IATA Matrix v1.0
            </div>
          </div>
        </header>

        {/* Live Deal Alert Banner */}
        {greatDeals.length > 0 && (
          <div className="w-full bg-gradient-to-r from-emerald-950/60 via-slate-900 to-slate-900 border border-emerald-500/40 rounded-xl p-3.5 flex items-center justify-between overflow-x-auto gap-4">
            <div className="flex items-center gap-2 text-xs font-bold text-emerald-400 uppercase tracking-wider shrink-0">
              <span>🔥</span> Live Moving Average Deal Alerts:
            </div>
            <div className="flex items-center gap-4 text-xs font-medium text-slate-300 shrink-0">
              {greatDeals.slice(0, 3).map((deal, idx) => (
                <div key={idx} className="flex items-center gap-1.5 bg-slate-950/60 px-3 py-1 rounded-lg border border-slate-800">
                  <span className="font-mono text-cyan-300 font-bold">{deal.origin} ➔ {deal.destination}</span>
                  <span className="text-emerald-400 font-bold">S${deal.current_price.toFixed(0)}</span>
                  <span className="text-[10px] text-slate-400">({deal.deal_info.badge})</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Active Tracked Routes Grid Section with Daily Cron Controls */}
        <TrackedRoutesList
          routes={trackedRoutes}
          scheduleStatus={scheduleStatus}
          onSelectRoute={handleSearch}
          onAddRoute={handleAddTrackedRoute}
          onDeleteRoute={handleDeleteTrackedRoute}
          onTriggerRefreshNow={handleTriggerDailyRefreshNow}
          onChangeDailyTime={handleChangeDailyTime}
          isLoading={isLoading}
        />

        {/* Flight Search Form */}
        <FlightSearchForm
          onSearch={handleSearch}
          onStopSearch={handleStopSearch}
          isLoading={isLoading}
        />

        {/* Transit Hub Visualizer Radar Graph */}
        <HubGraphVisualizer
          activeOrigin={searchResult?.origin?.code || "BWN"}
          activeDestination={searchResult?.destination?.code || "CTS"}
          activeHub={activeHubCode}
          onSelectHub={(hub) => setSelectedHub(hub)}
        />

        {/* Error / Status Banner if any */}
        {errorMsg && (
          <div className="p-4 bg-amber-950/60 border border-amber-500/40 rounded-xl text-amber-300 text-xs font-semibold flex items-center justify-between">
            <span>⚠️ {errorMsg}</span>
            <button
              onClick={() => setErrorMsg(null)}
              className="text-amber-400 hover:text-white font-bold ml-4"
            >
              ✕
            </button>
          </div>
        )}

        {/* Ready to Search Welcome Banner (when no search results yet) */}
        {!searchResult && !isLoading && (
          <div className="w-full bg-slate-900/60 border border-slate-800/80 rounded-2xl p-8 text-center space-y-3 shadow-xl backdrop-blur-md">
            <div className="w-16 h-16 bg-cyan-950/80 border border-cyan-500/30 rounded-2xl flex items-center justify-center text-3xl mx-auto shadow-inner text-cyan-400">
              ✈️
            </div>
            <h3 className="text-lg font-bold text-white">Ready for Route Intelligence Scan</h3>
            <p className="text-xs text-slate-400 max-w-lg mx-auto leading-relaxed">
              Click <strong className="text-cyan-300">&quot;⚡ Scan Route&quot;</strong> on any tracked route above, or configure custom origin and destination parameters then click <strong className="text-cyan-300">&quot;Find Range Deals ⚡&quot;</strong>.
            </p>
          </div>
        )}

        {/* Route Comparison Matrix */}
        {searchResult && (
          <RouteComparisonMatrix
            data={searchResult}
            selectedHub={selectedHub}
            onSelectHub={(hub) => setSelectedHub(hub)}
          />
        )}

        {/* Footer */}
        <footer className="border-t border-slate-800/80 pt-6 text-center text-xs text-slate-500 flex flex-col sm:flex-row justify-between items-center gap-2">
          <div>
            Built with Next.js, Tailwind CSS, FastAPI, Playwright, BeautifulSoup4 &amp; SQLite.
          </div>
          <div>
            AeroSplit AI Routing Engine &copy; 2026
          </div>
        </footer>
      </div>
    </main>
  );
}
