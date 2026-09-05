"use client";

import React, { useState } from "react";

interface Props {
  onSearch: (
    origin: string,
    destination: string,
    rangeStart: string,
    rangeEnd: string,
    tripDuration: number,
    tripType: string
  ) => void;
  onStopSearch?: () => void;
  isLoading: boolean;
}

const PRESET_ROUTES = [
  { orig: "BWN", dest: "CTS", label: "BWN ✈️ CTS (Sapporo Split)" },
  { orig: "BWN", dest: "NRT", label: "BWN ✈️ NRT (Tokyo)" },
  { orig: "BWN", dest: "KUL", label: "BWN ✈️ KUL (Kuala Lumpur)" },
  { orig: "SIN", dest: "CTS", label: "SIN ✈️ CTS (Singapore Split)" },
];

export default function FlightSearchForm({ onSearch, onStopSearch, isLoading }: Props) {
  const getNearFutureDates = () => {
    const today = new Date();
    const dStart = new Date(today.getTime() + 20 * 24 * 60 * 60 * 1000);
    const dEnd = new Date(today.getTime() + 27 * 24 * 60 * 60 * 1000);
    return {
      start: dStart.toISOString().split("T")[0],
      end: dEnd.toISOString().split("T")[0],
    };
  };

  const initialDates = getNearFutureDates();
  const [origin, setOrigin] = useState("BWN");
  const [destination, setDestination] = useState("TWU");
  const [rangeStart, setRangeStart] = useState(initialDates.start);
  const [rangeEnd, setRangeEnd] = useState(initialDates.end);
  const [tripDuration, setTripDuration] = useState<number>(7);
  const [tripType, setTripType] = useState("round_trip");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!origin || !destination) return;
    onSearch(origin, destination, rangeStart, rangeEnd, tripDuration, tripType);
  };

  const handleTripTypeChange = (newType: string) => {
    setTripType(newType);
  };

  const handlePresetClick = (orig: string, dest: string) => {
    setOrigin(orig);
    setDestination(dest);
  };

  const handleSwapAirports = () => {
    const temp = origin;
    setOrigin(destination);
    setDestination(temp);
  };

  return (
    <div className="w-full bg-slate-900/80 border border-slate-800 backdrop-blur-xl rounded-2xl p-7 shadow-2xl shadow-cyan-950/20 space-y-5">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div>
          <h2 className="text-2xl font-black text-white flex items-center gap-3">
            <span className="p-2.5 bg-gradient-to-tr from-cyan-500 to-blue-600 rounded-xl text-white text-lg shadow-md">
              🎯
            </span>
            Travel Date Range Best Deal Finder Engine
          </h2>
          <p className="text-sm text-slate-300 mt-1.5 font-medium">
            Select your travel window and parameters, then click &quot;Find Range Deals&quot; to compute optimal split routes.
          </p>
        </div>

        {/* Trip Type Selector Toggle */}
        <div className="flex items-center gap-2 bg-slate-950/90 p-2 rounded-xl border border-slate-800">
          <button
            type="button"
            onClick={() => handleTripTypeChange("round_trip")}
            className={`px-4 py-2 rounded-lg text-sm font-black transition-all cursor-pointer ${
              tripType === "round_trip"
                ? "bg-cyan-500 text-slate-950 shadow-md ring-2 ring-cyan-400/50"
                : "text-slate-300 hover:text-white"
            }`}
          >
            🔄 Round-Trip
          </button>
          <button
            type="button"
            onClick={() => handleTripTypeChange("one_way")}
            className={`px-4 py-2 rounded-lg text-sm font-black transition-all cursor-pointer ${
              tripType === "one_way"
                ? "bg-cyan-500 text-slate-950 shadow-md ring-2 ring-cyan-400/50"
                : "text-slate-300 hover:text-white"
            }`}
          >
            ➡️ One-Way
          </button>
        </div>
      </div>

      {/* Quick Presets Bar */}
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="text-sm font-extrabold text-slate-300 mr-1">Quick Presets:</span>
        {PRESET_ROUTES.map((route, i) => (
          <button
            key={i}
            type="button"
            onClick={() => handlePresetClick(route.orig, route.dest)}
            className="text-sm px-3.5 py-2 rounded-xl bg-slate-800/80 hover:bg-cyan-950 hover:text-cyan-300 text-slate-200 border border-slate-700/80 transition-all font-bold cursor-pointer"
          >
            {route.label}
          </button>
        ))}
      </div>

      {/* Prominent Active Travel Dates Indicator Bar */}
      <div className="p-4 bg-slate-950/90 border border-cyan-500/50 rounded-xl flex flex-col md:flex-row items-center justify-between text-sm gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-lg">🗓️</span>
          <span className="font-extrabold text-white uppercase tracking-wider text-sm">
            Selected Travel Window:
          </span>
          <span className="font-mono text-cyan-300 font-black bg-cyan-950/90 px-3.5 py-1.5 rounded-xl border border-cyan-500/40 text-base">
            📅 {rangeStart} ➔ {rangeEnd} ({tripDuration} Days Trip)
          </span>
        </div>
        <span className="text-slate-300 font-mono text-xs font-semibold">
          Press &quot;Find Range Deals&quot; to scan date combinations
        </span>
      </div>

      {/* Main Form Inputs with Date Range Window & Trip Duration */}
      <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-12 gap-3.5 items-end">
        {/* Origin Airport */}
        <div className="md:col-span-2">
          <label className="block text-sm font-bold text-slate-200 uppercase tracking-wider mb-2">
            Origin (IATA)
          </label>
          <input
            type="text"
            value={origin}
            onChange={(e) => setOrigin(e.target.value.toUpperCase())}
            placeholder="BWN"
            maxLength={4}
            required
            className="w-full bg-slate-950/90 border border-slate-700 focus:border-cyan-400 rounded-xl px-4 py-3 text-white font-mono font-black tracking-widest focus:outline-none focus:ring-2 focus:ring-cyan-500/20 transition-all text-base"
          />
        </div>

        {/* Swap Button */}
        <div className="md:col-span-1 flex items-center justify-center">
          <button
            type="button"
            onClick={handleSwapAirports}
            title="Swap Origin & Destination"
            className="h-[50px] w-full bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-bold rounded-xl transition-all flex items-center justify-center text-xl cursor-pointer"
          >
            ⇄
          </button>
        </div>

        {/* Destination Airport */}
        <div className="md:col-span-2">
          <label className="block text-sm font-bold text-slate-200 uppercase tracking-wider mb-2">
            Destination (IATA)
          </label>
          <input
            type="text"
            value={destination}
            onChange={(e) => setDestination(e.target.value.toUpperCase())}
            placeholder="CTS"
            maxLength={4}
            required
            className="w-full bg-slate-950/90 border border-slate-700 focus:border-cyan-400 rounded-xl px-4 py-3 text-white font-mono font-black tracking-widest focus:outline-none focus:ring-2 focus:ring-cyan-500/20 transition-all text-base"
          />
        </div>

        {/* Travel Window Start Date */}
        <div className="md:col-span-2">
          <label className="block text-sm font-bold text-cyan-300 uppercase tracking-wider mb-2">
            📅 Range Start Date
          </label>
          <input
            type="date"
            value={rangeStart}
            onChange={(e) => setRangeStart(e.target.value)}
            required
            className="w-full bg-slate-950/90 border border-cyan-500/60 focus:border-cyan-400 rounded-xl px-3 py-3 text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/20 transition-all font-bold text-sm cursor-pointer"
          />
        </div>

        {/* Travel Window End Date */}
        <div className="md:col-span-2">
          <label className="block text-sm font-bold text-cyan-300 uppercase tracking-wider mb-2">
            📅 Range End Date
          </label>
          <input
            type="date"
            value={rangeEnd}
            onChange={(e) => setRangeEnd(e.target.value)}
            required
            className="w-full bg-slate-950/90 border border-cyan-500/60 focus:border-cyan-400 rounded-xl px-3 py-3 text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/20 transition-all font-bold text-sm cursor-pointer"
          />
        </div>

        {/* Trip Duration Flexible Numeric Input */}
        <div className="md:col-span-1">
          <label className="block text-sm font-bold text-slate-200 uppercase tracking-wider mb-2">
            ⏱️ Days
          </label>
          <input
            type="number"
            min={1}
            max={60}
            value={tripDuration}
            onChange={(e) => setTripDuration(Math.max(1, parseInt(e.target.value, 10) || 1))}
            required
            placeholder="e.g. 10"
            className="w-full bg-slate-950/90 border border-slate-700 focus:border-cyan-400 rounded-xl px-3 py-3 text-white focus:outline-none focus:ring-2 focus:ring-cyan-500/20 transition-all font-bold text-sm"
          />
        </div>

        {/* Action Buttons: Submit / Stop Search */}
        <div className="md:col-span-2 flex items-center gap-2">
          {isLoading ? (
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                if (onStopSearch) onStopSearch();
              }}
              className="w-full h-[50px] bg-gradient-to-r from-rose-600 to-red-700 hover:from-rose-500 hover:to-red-600 text-white font-black rounded-xl shadow-lg shadow-rose-950/50 border border-rose-500/50 transition-all flex items-center justify-center gap-2 cursor-pointer text-sm animate-pulse"
            >
              <span className="text-base">🛑</span>
              <span>Stop Search</span>
            </button>
          ) : (
            <button
              type="submit"
              className="w-full h-[50px] bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-white font-black rounded-xl shadow-lg shadow-cyan-500/30 hover:shadow-cyan-500/50 transition-all flex items-center justify-center gap-2 cursor-pointer text-sm"
            >
              <span>Find Range Deals</span>
              <span className="text-base">⚡</span>
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
