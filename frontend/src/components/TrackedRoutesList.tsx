"use client";

import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { TrackedRouteItem } from "@/types/flight";
import PlatformPriceTable from "./PlatformPriceTable";

function fmtDate(dateStr?: string | null, fallback: string = "N/A"): string {
  if (!dateStr || dateStr.trim() === "") return fallback;
  try {
    const parts = dateStr.split("-");
    if (parts.length === 3) {
      const d = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
      if (!isNaN(d.getTime())) {
        return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
      }
    }
    return dateStr;
  } catch {
    return dateStr || fallback;
  }
}

export interface ScheduleStatus {
  status: string;
  schedule_type: string;
  daily_time: string;
  cron_expression: string;
  next_run_at?: string | null;
  last_run_at?: string | null;
  tracked_routes_count: number;
}

interface Props {
  routes: TrackedRouteItem[];
  scheduleStatus?: ScheduleStatus | null;
  onSelectRoute: (
    origin: string,
    destination: string,
    rangeStart: string,
    rangeEnd: string,
    tripDuration: number,
    tripType: string
  ) => void;
  onAddRoute: (
    origin: string,
    destination: string,
    rangeStart: string,
    rangeEnd: string,
    tripDuration: number,
    tripType: string
  ) => Promise<any>;
  onDeleteRoute: (id: number) => Promise<void>;
  onTriggerRefreshNow?: () => Promise<void>;
  onChangeDailyTime?: (timeStr: string) => Promise<void>;
  isLoading?: boolean;
}

export default function TrackedRoutesList({
  routes,
  scheduleStatus,
  onSelectRoute,
  onAddRoute,
  onDeleteRoute,
  onTriggerRefreshNow,
  onChangeDailyTime,
  isLoading = false,
}: Props) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [showTimeModal, setShowTimeModal] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (showAddModal || showTimeModal) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [showAddModal, showTimeModal]);

  const [customTime, setCustomTime] = useState(scheduleStatus?.daily_time || "02:00");
  
  const [newOrigin, setNewOrigin] = useState("BWN");
  const [newDestination, setNewDestination] = useState("KUL");
  const [newRangeStart, setNewRangeStart] = useState("2026-10-01");
  const [newRangeEnd, setNewRangeEnd] = useState("2026-10-31");
  const [newDuration, setNewDuration] = useState(10);
  const [newTripType, setNewTripType] = useState("round_trip");
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [refreshFeedback, setRefreshFeedback] = useState<{ type: "success" | "error" | "loading"; message: string } | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newOrigin || !newDestination) return;
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const result: any = await onAddRoute(newOrigin, newDestination, newRangeStart, newRangeEnd, newDuration, newTripType);
      setShowAddModal(false);

      if (result && result.status === "no_route_in_range") {
        setRefreshFeedback({
          type: "error",
          message: `Added ${newOrigin} ➔ ${newDestination}, but no scheduled flights or valid transit routes were found within ${newRangeStart} to ${newRangeEnd}.`,
        });
      } else {
        setRefreshFeedback({
          type: "success",
          message: `Successfully tracked ${newOrigin} ➔ ${newDestination}! Live rates recorded.`,
        });
      }

      setTimeout(() => {
        const targetId = result?.id ? `route-card-${result.id}` : null;
        const el = (targetId ? document.getElementById(targetId) : null) || document.getElementById('tracked-routes-container');
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 400);
    } catch (err: any) {
      setSubmitError(err?.message || "Failed to start tracking route. Please verify airport codes.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTriggerRefresh = async () => {
    if (!onTriggerRefreshNow) return;
    setIsRefreshing(true);
    setRefreshFeedback({
      type: "loading",
      message: "Scraping and refreshing real-time prices across all active tracked routes...",
    });
    try {
      await onTriggerRefreshNow();
      setRefreshFeedback({
        type: "success",
        message: `Daily refresh complete! Refreshed price data across all ${routes.length} active routes.`,
      });
      setTimeout(() => {
        setRefreshFeedback(null);
      }, 6000);
    } catch (err: any) {
      setRefreshFeedback({
        type: "error",
        message: err?.message || "Failed to complete daily price refresh. Please check server connection.",
      });
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleTimeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!onChangeDailyTime || !customTime) return;
    try {
      await onChangeDailyTime(customTime);
      setShowTimeModal(false);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="w-full bg-slate-900/80 border border-slate-800 backdrop-blur-xl rounded-2xl p-6 shadow-2xl shadow-cyan-950/20 space-y-5">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-xl font-bold text-white flex items-center gap-2">
            <span className="p-2 bg-gradient-to-tr from-cyan-500 to-indigo-600 rounded-lg text-white text-sm shadow-md">
              📡
            </span>
            Active Tracked Routes &amp; Range Period Monitoring
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Real-time background price tracking across active travel windows in SGD (S$).
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={() => setShowTimeModal(true)}
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 hover:border-slate-600 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer shadow-md active:scale-95"
          >
            <span>⚙️ Config Time ({scheduleStatus?.daily_time || "02:00"})</span>
          </button>

          <button
            type="button"
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-black rounded-xl text-xs transition-all flex items-center gap-1.5 cursor-pointer shadow-lg shadow-cyan-500/20 active:scale-95"
          >
            <span>➕ Track New Route Range</span>
          </button>
        </div>
      </div>

      {/* Prominent Daily Cron Refresh Schedule Status Bar */}
      <div className="p-3.5 bg-slate-950/90 border border-cyan-500/40 rounded-xl flex flex-col md:flex-row items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-cyan-950 border border-cyan-500/30 rounded-xl flex items-center justify-center text-lg shrink-0">
            ⏰
          </div>
          <div>
            <div className="font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <span>Daily Scheduled Background Refresh Engine</span>
              <span className="px-2.5 py-0.5 bg-emerald-500/20 text-emerald-300 rounded-full border border-emerald-500/40 text-[10px] font-extrabold animate-pulse">
                ACTIVE @ {scheduleStatus?.daily_time || "02:00"} UTC
              </span>
            </div>
            <div className="text-slate-400 font-mono text-[11px] mt-0.5">
              Refreshes prices for all {routes.length} active routes daily at <strong className="text-cyan-300">{scheduleStatus?.daily_time || "02:00"} AM UTC</strong>.
              {scheduleStatus?.next_run_at && (
                <span className="text-emerald-400 ml-2 font-semibold">
                  (Next Run: {new Date(scheduleStatus.next_run_at).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })})
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={handleTriggerRefresh}
            disabled={isRefreshing}
            className="px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-600 hover:from-emerald-400 hover:to-teal-500 text-slate-950 font-black rounded-xl text-xs shadow-lg shadow-emerald-950/50 transition-all cursor-pointer disabled:opacity-60 flex items-center gap-2 active:scale-95"
          >
            {isRefreshing ? (
              <>
                <span className="w-3 h-3 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                <span>Refreshing Routes...</span>
              </>
            ) : (
              <>
                <span>⚡</span>
                <span>Run Daily Refresh Now</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Refresh Status / Progress Alert Banner */}
      {refreshFeedback && (
        <div className={`p-4 rounded-xl border flex items-center justify-between gap-3 text-sm animate-fadeIn ${
          refreshFeedback.type === "loading"
            ? "bg-cyan-950/70 border-cyan-500/50 text-cyan-200"
            : refreshFeedback.type === "success"
            ? "bg-emerald-950/80 border-emerald-500/60 text-emerald-200"
            : "bg-rose-950/80 border-rose-500/60 text-rose-200"
        }`}>
          <div className="flex items-center gap-3">
            {refreshFeedback.type === "loading" && (
              <span className="w-4 h-4 border-2 border-cyan-300 border-t-transparent rounded-full animate-spin shrink-0" />
            )}
            {refreshFeedback.type === "success" && <span className="text-lg shrink-0">✅</span>}
            {refreshFeedback.type === "error" && <span className="text-lg shrink-0">⚠️</span>}
            <span className="font-bold">{refreshFeedback.message}</span>
          </div>
          {refreshFeedback.type !== "loading" && (
            <button
              type="button"
              onClick={() => setRefreshFeedback(null)}
              className="text-xs font-bold px-2 py-1 rounded bg-black/40 hover:bg-black/60 cursor-pointer"
            >
              ✕
            </button>
          )}
        </div>
      )}

      {/* Configure Daily Time Form Modal Dialog */}
      {showTimeModal && mounted && createPortal(
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowTimeModal(false);
          }}
        >
          <div className="relative w-full max-w-md bg-slate-900 border-2 border-indigo-500/80 rounded-2xl p-6 shadow-2xl shadow-indigo-950/80 space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <span className="text-xl">⏰</span>
                <h3 className="text-base font-black text-white">Daily Refresh Schedule Time</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowTimeModal(false)}
                className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white flex items-center justify-center text-sm font-bold cursor-pointer"
              >
                ✕
              </button>
            </div>
            <p className="text-xs text-slate-400">
              Configure the exact UTC time when AeroSplit background engine automatically scans and records authentic Google Flights prices for all tracked routes.
            </p>
            <form onSubmit={handleTimeSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase mb-1.5">
                  Daily Execution Time (UTC)
                </label>
                <input
                  type="time"
                  value={customTime}
                  onChange={(e) => setCustomTime(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-sm text-white font-mono font-bold focus:border-indigo-400 focus:outline-none"
                />
              </div>
              <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowTimeModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-bold cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2.5 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-400 hover:to-purple-500 text-white font-black rounded-xl text-xs shadow-md cursor-pointer"
                >
                  Save Schedule Time
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* Add New Tracked Route Form Modal Dialog */}
      {showAddModal && mounted && createPortal(
        <div 
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn"
          onClick={(e) => {
            if (e.target === e.currentTarget) setShowAddModal(false);
          }}
        >
          <div className="relative w-full max-w-lg bg-slate-900 border-2 border-cyan-500/80 rounded-2xl p-5 shadow-2xl shadow-cyan-950/80 space-y-3.5 max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 via-blue-600 to-indigo-600 flex items-center justify-center text-white text-base font-bold shadow-md shadow-cyan-500/30">
                  ✈️
                </div>
                <div>
                  <h3 className="text-base font-black text-white">Track New Route Range</h3>
                  <p className="text-[11px] text-slate-400">Monitor live prices, split routing, and receive deal alerts.</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowAddModal(false)}
                className="w-7 h-7 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white flex items-center justify-center text-xs font-bold cursor-pointer transition-colors"
              >
                ✕
              </button>
            </div>

            {submitError && (
              <div className="p-3 bg-rose-950/80 border border-rose-500/60 rounded-xl text-rose-200 text-xs font-bold flex items-center gap-2 animate-fadeIn">
                <span className="text-sm">⚠️</span>
                <span>{submitError}</span>
              </div>
            )}

            {/* Quick Route Preset Chips */}
            <div>
              <label className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">
                Popular Route Presets
              </label>
              <div className="flex flex-wrap gap-2">
                {[
                  { o: "BWN", d: "KUL", label: "BWN ⇄ KUL" },
                  { o: "KUL", d: "NRT", label: "KUL ⇄ NRT" },
                  { o: "BWN", d: "TWU", label: "BWN ⇄ TWU" },
                  { o: "SIN", d: "CTS", label: "SIN ⇄ CTS" },
                  { o: "BWN", d: "SIN", label: "BWN ⇄ SIN" },
                  { o: "BWN", d: "BKK", label: "BWN ⇄ BKK" },
                ].map((preset) => (
                  <button
                    key={preset.label}
                    type="button"
                    onClick={() => {
                      setNewOrigin(preset.o);
                      setNewDestination(preset.d);
                    }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-mono font-bold transition-all cursor-pointer ${
                      newOrigin === preset.o && newDestination === preset.d
                        ? "bg-cyan-500 text-slate-950 shadow-md font-black"
                        : "bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
                    }`}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            <form onSubmit={handleCreate} className="space-y-3">
              {/* Origin & Destination Inputs */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase mb-1">
                    Origin IATA <span className="text-cyan-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={newOrigin}
                    onChange={(e) => setNewOrigin(e.target.value.toUpperCase())}
                    maxLength={4}
                    required
                    placeholder="e.g. BWN"
                    className="w-full bg-slate-950 border border-slate-700 focus:border-cyan-400 rounded-xl px-3 py-2 text-sm text-white font-mono font-black uppercase tracking-wider focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase mb-1">
                    Destination IATA <span className="text-cyan-400">*</span>
                  </label>
                  <input
                    type="text"
                    value={newDestination}
                    onChange={(e) => setNewDestination(e.target.value.toUpperCase())}
                    maxLength={4}
                    required
                    placeholder="e.g. KUL"
                    className="w-full bg-slate-950 border border-slate-700 focus:border-cyan-400 rounded-xl px-3 py-2 text-sm text-white font-mono font-black uppercase tracking-wider focus:outline-none"
                  />
                </div>
              </div>

              {/* Trip Type Selector */}
              <div>
                <label className="block text-xs font-bold text-slate-300 uppercase mb-1">
                  Trip Type
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setNewTripType("round_trip")}
                    className={`py-2 px-3 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
                      newTripType === "round_trip"
                        ? "bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-black shadow-md"
                        : "bg-slate-950 border border-slate-700 text-slate-400 hover:text-white"
                    }`}
                  >
                    <span>⇄</span> Round-Trip
                  </button>
                  <button
                    type="button"
                    onClick={() => setNewTripType("one_way")}
                    className={`py-2 px-3 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center justify-center gap-1.5 ${
                      newTripType === "one_way"
                        ? "bg-gradient-to-r from-cyan-500 to-blue-600 text-slate-950 font-black shadow-md"
                        : "bg-slate-950 border border-slate-700 text-slate-400 hover:text-white"
                    }`}
                  >
                    <span>➔</span> One-Way
                  </button>
                </div>
              </div>

              {/* Travel Range & Duration */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase mb-1">
                    Range Start <span className="text-cyan-400">*</span>
                  </label>
                  <input
                    type="date"
                    value={newRangeStart}
                    onChange={(e) => setNewRangeStart(e.target.value)}
                    required
                    className="w-full bg-slate-950 border border-slate-700 focus:border-cyan-400 rounded-xl px-3 py-2 text-xs text-white font-mono font-bold focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase mb-1">
                    Range End <span className="text-cyan-400">*</span>
                  </label>
                  <input
                    type="date"
                    value={newRangeEnd}
                    onChange={(e) => setNewRangeEnd(e.target.value)}
                    required
                    className="w-full bg-slate-950 border border-slate-700 focus:border-cyan-400 rounded-xl px-3 py-2 text-xs text-white font-mono font-bold focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-slate-300 uppercase mb-1">
                    Duration (Days) <span className="text-cyan-400">*</span>
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={60}
                    value={newDuration}
                    onChange={(e) => setNewDuration(Math.max(1, parseInt(e.target.value, 10) || 1))}
                    required
                    className="w-full bg-slate-950 border border-slate-700 focus:border-cyan-400 rounded-xl px-3 py-2 text-xs text-white font-mono font-bold focus:outline-none"
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-2.5 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-bold transition-all cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-black rounded-xl text-xs shadow-lg shadow-cyan-500/30 transition-all cursor-pointer disabled:opacity-50 flex items-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <span className="w-3.5 h-3.5 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                      <span>Tracking & Scraping Live Rates...</span>
                    </>
                  ) : (
                    <>
                      <span>➕</span>
                      <span>Start Tracking Route Range</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}

      {/* Grid of Tracked Route Cards or Empty State */}
      {routes.length === 0 ? (
        <div className="p-8 border border-dashed border-slate-800 rounded-xl flex flex-col items-center justify-center text-center space-y-3 bg-slate-950/40">
          <div className="w-12 h-12 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center text-2xl">
            ✈️
          </div>
          <div>
            <h4 className="text-sm font-bold text-white">No Tracked Routes Active</h4>
            <p className="text-xs text-slate-400 max-w-sm mt-1">
              Start tracking route date ranges to automatically record daily Google Flights prices and receive moving average deal alerts.
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowAddModal(true)}
            className="px-4 py-2 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 font-black rounded-xl text-xs shadow-md cursor-pointer transition-all"
          >
            ➕ Track New Route Range
          </button>
        </div>
      ) : (
        <div id="tracked-routes-container" className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {routes.map((route) => {
          const obLegs = (route.outbound_legs && route.outbound_legs.length > 0)
            ? route.outbound_legs
            : [route.leg1, route.leg2].filter((l): l is NonNullable<typeof l> => Boolean(l));

          const retLegs = (route.return_legs && route.return_legs.length > 0)
            ? route.return_legs
            : [route.return_leg1, route.return_leg2].filter((l): l is NonNullable<typeof l> => Boolean(l));

          const isNoRouteFound = route.status === "no_route_in_range" || (route.estimated_price === 0 && obLegs.length === 0);
          const isGreen = !isNoRouteFound && route.deal_info?.tier === "green";
          const isYellow = !isNoRouteFound && route.deal_info?.tier === "yellow";

          return (
            <div
              key={route.id}
              id={`route-card-${route.id}`}
              className={`p-4 rounded-xl border transition-all flex flex-col justify-between space-y-3 relative ${
                isNoRouteFound
                  ? "bg-slate-950/80 border-amber-500/40 shadow-lg shadow-amber-950/20"
                  : isGreen
                  ? "bg-gradient-to-b from-emerald-950/40 via-slate-950/80 to-slate-950/90 border-emerald-500/50 shadow-lg shadow-emerald-950/30"
                  : isYellow
                  ? "bg-slate-950/70 border-slate-800 hover:border-slate-700"
                  : "bg-slate-950/70 border-slate-800"
              }`}
            >
              {/* Card Header: Airport Pair & Badges */}
              <div>
                <div className="flex items-center justify-between gap-2 mb-2.5">
                  <div className="flex items-center gap-2 font-mono text-lg font-black text-white">
                    <span>{route.origin.code}</span>
                    <span className="text-cyan-400">{route.trip_type === "one_way" ? "➔" : "⇄"}</span>
                    <span>{route.destination.code}</span>
                    <span className="text-xs text-slate-400 font-sans font-medium ml-1">
                      ({route.destination.city})
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="px-2.5 py-1 rounded-lg text-xs font-black uppercase bg-slate-900 border border-slate-700 text-cyan-300">
                      {route.trip_type === "one_way" ? "One-Way" : "Round-Trip"}
                    </span>
                    {isNoRouteFound && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse">
                        No Route In Range
                      </span>
                    )}
                  </div>
                </div>

                {/* Range Period Banner */}
                <div className="p-2.5 bg-slate-900/90 rounded-xl border border-slate-800 text-sm font-mono space-y-1 mb-3.5">
                  <div className="flex justify-between text-slate-300">
                    <span className="text-xs text-cyan-300 font-extrabold">📅 Active Window:</span>
                    <span className="text-xs text-slate-300 font-bold">{route.trip_duration_days} Days</span>
                  </div>
                  <div className="text-xs text-white font-black">
                    {route.range_start} ➔ {route.range_end}
                  </div>
                </div>

                {/* Pricing & Transit Hub Info */}
                <div className="flex items-baseline justify-between mb-3.5">
                  <div>
                    <span className="text-xs text-slate-400 block font-mono font-bold">Lowest Deal</span>
                    {isNoRouteFound ? (
                      <span className="text-lg font-black text-amber-400 font-mono">
                        No Flights Found
                      </span>
                    ) : (
                      <span className="text-3xl font-black text-white font-mono">
                        S${route.estimated_price > 0 ? route.estimated_price.toFixed(0) : "N/A"}
                      </span>
                    )}
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-slate-400 block font-mono font-bold">Transit Hub</span>
                    <span className="text-sm font-extrabold text-indigo-300 font-mono">
                      {isNoRouteFound && (!route.best_hub || route.best_hub === "N/A")
                        ? "No Valid Hub"
                        : route.best_hub === "DIRECT"
                        ? "Direct Non-Stop"
                        : `Via ${route.best_hub}`}
                    </span>
                  </div>
                </div>

                {/* Body Content */}
                {isNoRouteFound ? (
                  <div className="p-3.5 bg-amber-950/30 border border-amber-500/40 rounded-xl space-y-2 text-left my-2.5">
                    <div className="flex items-center gap-2 text-amber-300 font-black text-xs uppercase tracking-wider">
                      <span className="text-base">⚠️</span>
                      <span>No Flight Route Found Within Specified Range</span>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed font-medium">
                      {route.status_message || `No operating airlines or connecting flight routes could be verified between ${route.origin.code} and ${route.destination.code} within the travel window (${route.range_start} ➔ ${route.range_end}, ${route.trip_duration_days} days).`}
                    </p>
                    <div className="p-2 bg-slate-950/80 rounded-lg border border-slate-800 text-[11px] text-slate-400 font-mono space-y-1">
                      <div className="flex justify-between">
                        <span className="text-slate-500">Route Pair:</span>
                        <span className="text-white font-bold">{route.origin.code} ➔ {route.destination.code}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Monitored Window:</span>
                        <span className="text-cyan-300 font-bold">{route.range_start} ➔ {route.range_end}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-500">Trip Length:</span>
                        <span className="text-slate-300 font-bold">{route.trip_duration_days} Days ({route.trip_type === "one_way" ? "One-Way" : "Round-Trip"})</span>
                      </div>
                    </div>
                    <div className="text-[11px] text-amber-300/80 flex items-center gap-1.5 pt-0.5">
                      <span>💡</span>
                      <span>Tip: Try widening the date window or choosing another hub airport.</span>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="mb-3 space-y-2">
                      <div className="flex items-center gap-2 text-xs font-black uppercase tracking-wider text-cyan-400 mb-1">
                        <span className="w-4 h-px bg-cyan-500/60 block" />
                        Outbound ({obLegs.length} {obLegs.length === 1 ? "Flight" : "Legs"})
                        <span className="flex-1 h-px bg-cyan-500/30 block" />
                      </div>
                      {obLegs.map((leg, lIdx) => (
                        <React.Fragment key={`ob-leg-${lIdx}`}>
                          <div className="p-3 bg-slate-900/90 border border-slate-800 rounded-xl space-y-1.5">
                            <div className="flex items-center justify-between gap-2">
                              <span className="font-mono text-xs font-black text-cyan-300 uppercase tracking-wider">
                                <span className="text-slate-500 mr-1.5">Leg {lIdx + 1}:</span>
                                {leg.origin} ➔ {leg.destination} <span className="text-slate-400 font-medium">({fmtDate(leg.departure_date || route.range_start)})</span>
                              </span>
                              {leg.flight_number && leg.flight_number !== "N/A" && (
                                <span className="text-xs font-bold text-slate-400 font-mono">{leg.flight_number}</span>
                              )}
                            </div>
                            <div className="text-xs text-white font-bold truncate">{leg.airline}</div>
                            <div className="flex items-center justify-between text-xs text-slate-300 font-mono">
                              <span>
                                <span className="text-white font-extrabold">{leg.departure_time}</span>
                                {" "}→{" "}
                                <span className="text-white font-extrabold">{leg.arrival_time}</span>
                              </span>
                              <span className="text-slate-400">{leg.duration}</span>
                              <span className="text-emerald-400 font-black">S${leg.price.toFixed(0)}</span>
                            </div>
                            {leg.platform_prices && Object.keys(leg.platform_prices).length > 0 && (
                              <PlatformPriceTable compact platformPrices={leg.platform_prices} cheapestPlatform={leg.cheapest_platform} />
                            )}
                          </div>

                          {/* Layover Indicator between legs */}
                          {leg.layover_after && (
                            <div className="flex items-center justify-center my-1">
                              <div className="flex items-center gap-1.5 px-3 py-1 bg-amber-950/40 border border-amber-500/40 text-amber-300 rounded-full text-[11px] font-mono font-bold shadow-sm">
                                <span>⏳</span>
                                <span>Layover in <strong className="text-amber-200">{leg.layover_after.airport}</strong> ({leg.layover_after.duration})</span>
                              </div>
                            </div>
                          )}
                        </React.Fragment>
                      ))}
                    </div>

                    {/* ── RETURN ──────────────────────────────────── */}
                    {route.trip_type !== "one_way" && retLegs.length > 0 && (
                      <div className="mb-3 space-y-2">
                        <div className="flex items-center gap-2 text-xs font-black uppercase tracking-wider text-amber-400 mb-1">
                          <span className="w-4 h-px bg-amber-500/60 block" />
                          Return ({retLegs.length} {retLegs.length === 1 ? "Flight" : "Legs"})
                          <span className="flex-1 h-px bg-amber-500/30 block" />
                        </div>
                        {retLegs.map((leg, rIdx) => (
                          <React.Fragment key={`ret-leg-${rIdx}`}>
                            <div className="p-3 bg-slate-900/90 border border-amber-500/30 rounded-xl space-y-1.5">
                              <div className="flex items-center justify-between gap-2">
                                <span className="font-mono text-xs font-black text-amber-300 uppercase tracking-wider">
                                  <span className="text-slate-500 mr-1.5">Leg {rIdx + 1}:</span>
                                  {leg.origin} ➔ {leg.destination} <span className="text-slate-400 font-medium">({fmtDate(leg.departure_date || route.range_end)})</span>
                                </span>
                                {leg.flight_number && leg.flight_number !== "N/A" && (
                                  <span className="text-xs font-bold text-slate-400 font-mono">{leg.flight_number}</span>
                                )}
                              </div>
                              <div className="text-xs text-white font-bold truncate">{leg.airline}</div>
                              <div className="flex items-center justify-between text-xs text-slate-300 font-mono">
                                <span>
                                  <span className="text-white font-extrabold">{leg.departure_time}</span>
                                  {" "}→{" "}
                                  <span className="text-white font-extrabold">{leg.arrival_time}</span>
                                </span>
                                <span className="text-slate-400">{leg.duration}</span>
                                <span className="text-emerald-400 font-black">S${leg.price.toFixed(0)}</span>
                              </div>
                              {leg.platform_prices && Object.keys(leg.platform_prices).length > 0 && (
                                <PlatformPriceTable compact platformPrices={leg.platform_prices} cheapestPlatform={leg.cheapest_platform} />
                              )}
                            </div>

                            {/* Layover Indicator between legs */}
                            {leg.layover_after && (
                              <div className="flex items-center justify-center my-1">
                                <div className="flex items-center gap-1.5 px-3 py-1 bg-amber-950/40 border border-amber-500/40 text-amber-300 rounded-full text-[11px] font-mono font-bold shadow-sm">
                                  <span>⏳</span>
                                  <span>Layover in <strong className="text-amber-200">{leg.layover_after.airport}</strong> ({leg.layover_after.duration})</span>
                                </div>
                              </div>
                            )}
                          </React.Fragment>
                        ))}
                      </div>
                    )}
                  </>
                )}

                {/* Deal Badge */}
                <div className="flex items-center justify-between pt-1 border-t border-slate-800">
                  <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                    isNoRouteFound
                      ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 font-black"
                      : isGreen
                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                      : "bg-slate-800 text-slate-400"
                  }`}>
                    {isNoRouteFound ? "No Route In Range" : (route.deal_info?.badge || "Tracked")}
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    60d Avg: S${route.avg_60d ? route.avg_60d.toFixed(0) : "N/A"}
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 pt-2">
                <button
                  type="button"
                  disabled={isLoading}
                  onClick={() =>
                    onSelectRoute(
                      route.origin.code,
                      route.destination.code,
                      route.range_start,
                      route.range_end,
                      route.trip_duration_days,
                      route.trip_type
                    )
                  }
                  className="flex-1 py-1.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white text-xs font-extrabold rounded-lg transition-all shadow-md flex items-center justify-center gap-1 cursor-pointer disabled:opacity-50"
                >
                  <span>{isNoRouteFound ? "⚡ Re-Scan Range" : "⚡ Scan Route"}</span>
                </button>
                <button
                  type="button"
                  onClick={() => onDeleteRoute(route.id)}
                  title="Stop tracking this route range"
                  className="px-2.5 py-1.5 bg-slate-800 hover:bg-rose-950 hover:text-rose-300 text-slate-400 border border-slate-700/60 rounded-lg text-xs font-bold transition-all cursor-pointer"
                >
                  🗑️
                </button>
              </div>
            </div>
          );
        })}
        </div>
      )}
    </div>
  );
}
