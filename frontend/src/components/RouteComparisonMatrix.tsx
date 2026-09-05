"use client";

import React from "react";
import { SearchResponse } from "@/types/flight";
import DealScoreIndicator from "./DealScoreIndicator";
import PlatformPriceTable from "./PlatformPriceTable";

interface Props {
  data: SearchResponse;
  selectedHub?: string | null;
  onSelectHub?: (hubCode: string) => void;
}

/**
 * Robust date formatting utility.
 * Converts ISO date string "YYYY-MM-DD" to human-readable "Oct 15, 2026".
 * Guarantees a non-empty return value.
 */
function fmtDate(dateStr?: string | null, fallback: string = "N/A"): string {
  if (!dateStr || dateStr.trim() === "" || dateStr === "undefined" || dateStr === "null") {
    return fallback;
  }
  try {
    const parts = dateStr.split("-");
    if (parts.length === 3) {
      const d = new Date(parseInt(parts[0]), parseInt(parts[1]) - 1, parseInt(parts[2]));
      if (!isNaN(d.getTime())) {
        return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
      }
    }
    return dateStr;
  } catch {
    return dateStr || fallback;
  }
}

/** Format time string: ensures non-empty. Input is "HH:MM" from backend. */
function fmtTime(t?: string): string {
  if (!t || t.trim() === "") return "--:--";
  return t;
}

export default function RouteComparisonMatrix({ data, selectedHub, onSelectHub }: Props) {
  const isRoundTrip = data.trip_type !== "one_way";

  const outboundDirect = data.direct_option;
  const hasDirectFlight = outboundDirect?.has_direct_flight ?? (outboundDirect?.price > 0);

  const outboundSplits = data.split_options || [];
  const bestOutboundSplit = outboundSplits.find((s) => s.is_best_split) || outboundSplits[0];

  const returnDirect = isRoundTrip ? (data.return_direct_option || outboundDirect) : outboundDirect;
  const returnSplits = isRoundTrip ? (data.return_split_options || outboundSplits) : outboundSplits;
  const bestReturnSplit = returnSplits.find((s) => s.is_best_split) || returnSplits[0];

  const combinedDirectPrice = hasDirectFlight
    ? (data.total_round_trip_direct_price || (isRoundTrip ? outboundDirect.price * 2 : outboundDirect.price))
    : 0;

  const combinedBestSplitPrice = data.total_round_trip_best_split_price || (bestOutboundSplit ? (isRoundTrip ? bestOutboundSplit.total_price * 2 : bestOutboundSplit.total_price) : 0);
  const combinedSavings = hasDirectFlight ? (data.round_trip_savings || (combinedDirectPrice - combinedBestSplitPrice)) : 0;

  const range = data.range_analysis;

  const depDate = fmtDate(data.outbound_date);
  const retDate = fmtDate(data.return_date);

  return (
    <div className="w-full space-y-6">
      {/* Scraper Health Banner */}
      {data.scraper_status && (
        <div className={`p-4 rounded-xl border text-sm flex items-center justify-between gap-4 ${
          data.scraper_status.is_live
            ? "bg-emerald-950/60 border-emerald-500/40 text-emerald-200"
            : "bg-amber-950/60 border-amber-500/40 text-amber-200"
        }`}>
          <div className="flex items-center gap-2.5">
            <span className="text-lg">{data.scraper_status.is_live ? "🟢" : "⚡"}</span>
            <div>
              <span className="font-extrabold uppercase tracking-wider block text-xs text-white">
                Scraper Diagnostic: {data.scraper_status.status_badge}
              </span>
              <span className="text-xs font-medium opacity-90">{data.scraper_status.message}</span>
            </div>
          </div>
          <span className="text-xs font-mono font-bold bg-slate-950/80 px-3 py-1 rounded border border-slate-800 text-slate-300 shrink-0">
            Source: {data.scraper_status.source}
          </span>
        </div>
      )}

      {/* Confirmed Travel Dates Banner */}
      <div className="w-full bg-gradient-to-r from-cyan-950 via-slate-900 to-indigo-950 border-2 border-cyan-400/80 p-5 rounded-2xl flex flex-col md:flex-row items-center justify-between gap-4 shadow-2xl">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 bg-cyan-500 text-slate-950 font-black text-2xl rounded-2xl flex items-center justify-center shadow-lg shadow-cyan-500/30 shrink-0">
            🗓️
          </div>
          <div>
            <span className="text-xs font-bold text-cyan-400 uppercase tracking-widest block">
              CONFIRMED FLIGHT TRAVEL DATES
            </span>
            <div className="flex flex-wrap items-center gap-3 mt-1">
              <span className="text-lg font-black font-mono bg-slate-950/90 px-3.5 py-1.5 rounded-xl border border-cyan-500/60 text-cyan-300 shadow-md">
                🛫 Depart: {depDate}
              </span>
              {isRoundTrip && (
                <span className="text-lg font-black font-mono bg-slate-950/90 px-3.5 py-1.5 rounded-xl border border-indigo-500/60 text-indigo-300 shadow-md">
                  🛬 Return: {retDate}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="text-right shrink-0">
          <span className="text-xs text-slate-400 block font-mono">Route</span>
          <span className="text-lg font-black text-white font-mono">
            {data.origin.code} {isRoundTrip ? "⇄" : "➔"} {data.destination.code}
          </span>
        </div>
      </div>

      {/* Route Header with Travel Range Summary */}
      <div className="flex flex-col md:flex-row md:items-center justify-between bg-slate-900/80 border border-slate-800 p-6 rounded-2xl backdrop-blur-xl gap-4 shadow-xl">
        <div>
          <div className="flex flex-wrap items-center gap-3">
            <span className="px-3 py-1 bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 rounded-full text-xs font-bold font-mono">
              {isRoundTrip ? "🔄 ROUND-TRIP ENGINE" : "➡️ ONE-WAY ENGINE"}
            </span>
            {!hasDirectFlight && (
              <span className="px-3 py-1 bg-amber-500/20 text-amber-300 border border-amber-500/40 rounded-full text-xs font-bold font-mono">
                ⚠️ NO DIRECT FLIGHT OPERATING (SPLIT REQUIRED)
              </span>
            )}
            {range && (
              <span className="text-slate-300 text-xs font-semibold bg-slate-800 px-3.5 py-1 rounded-full border border-slate-700 font-mono">
                📅 Window: {fmtDate(range.range_start)} ➔ {fmtDate(range.range_end)} ({range.trip_duration_days}d)
              </span>
            )}
          </div>
          <h3 className="text-2xl font-extrabold text-white mt-2">
            {data.origin.name} ({data.origin.code}) {isRoundTrip ? "⇄" : "➔"} {data.destination.name} ({data.destination.code})
          </h3>
        </div>
        {range && (
          <div className="p-4 bg-gradient-to-r from-emerald-950/90 to-teal-900/50 border border-emerald-500/40 rounded-xl flex items-center gap-4 shadow-lg shrink-0">
            <div className="text-3xl">🌟</div>
            <div>
              <div className="text-xs font-bold text-emerald-400 uppercase tracking-wider">Cheapest Dates Found</div>
              <div className="text-base font-black text-white font-mono mt-0.5">
                🛫 {fmtDate(range.cheapest_departure_date)} → 🛬 {fmtDate(range.cheapest_return_date)}
              </div>
              <p className="text-xs text-emerald-200/90 font-bold mt-0.5">
                S${range.cheapest_package_price.toFixed(0)} via {range.cheapest_hub} {hasDirectFlight ? `(Save S$${range.max_range_savings.toFixed(0)})` : "(Optimal Split Route)"}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Date Candidates Grid */}
      {range?.date_candidates && range.date_candidates.length > 0 && (
        <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-3">
          <h4 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <span>📅</span> Date Candidates ({fmtDate(range.range_start)} to {fmtDate(range.range_end)})
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3">
            {range.date_candidates.map((cand, idx) => (
              <div key={idx} className={`p-4 rounded-xl border transition-all ${
                cand.is_cheapest_in_range
                  ? "bg-gradient-to-b from-emerald-950/80 to-slate-900 border-emerald-500/60 shadow-lg ring-1 ring-emerald-400/50"
                  : "bg-slate-950/70 border-slate-800 hover:border-slate-700"
              }`}>
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="font-mono text-slate-200 font-extrabold">🛫 {fmtDate(cand.departure_date)}</span>
                  {cand.is_cheapest_in_range && (
                    <span className="text-xs bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded font-black border border-emerald-500/40 uppercase">CHEAPEST</span>
                  )}
                </div>
                <div className="text-xs text-slate-300 font-mono font-bold mb-2">🛬 {fmtDate(cand.return_date, "One-way")}</div>
                <div className="flex items-baseline justify-between border-t border-slate-800/80 pt-2">
                  <span className="text-xl font-black text-white">S${cand.best_split_price.toFixed(0)}</span>
                  <span className="text-xs text-emerald-400 font-extrabold">
                    {hasDirectFlight && cand.savings > 0 ? `Save S$${cand.savings.toFixed(0)}` : "Best Split"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No Route Available Banner */}
      {!hasDirectFlight && outboundSplits.length === 0 && (
        <div className="w-full p-8 bg-slate-900/90 border-2 border-rose-500/50 rounded-2xl text-center space-y-3 shadow-2xl shadow-rose-950/30 animate-fadeIn">
          <div className="text-4xl">✈️🚫</div>
          <h3 className="text-xl font-extrabold text-white">No Route Available</h3>
          <p className="text-sm text-slate-300 max-w-md mx-auto">
            No operating direct non-stop flights or transit split connections exist between <strong className="text-cyan-300">{data.origin.code} ({data.origin.name})</strong> and <strong className="text-cyan-300">{data.destination.code} ({data.destination.name})</strong>.
          </p>
          <div className="text-xs text-slate-400 font-mono">Please select a different origin or destination pair.</div>
        </div>
      )}

      {/* 3-Column Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Card 1: Direct Non-Stop */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between hover:border-slate-700 transition-all shadow-xl">
          <div>
            <div className="flex items-center justify-between mb-4">
              <span className="px-3 py-1 bg-slate-800 text-slate-300 rounded-full text-xs font-semibold uppercase tracking-wider border border-slate-700">
                Direct Non-Stop Option
              </span>
              {!hasDirectFlight && (
                <span className="text-xs bg-amber-500/20 text-amber-300 px-2 py-0.5 rounded border border-amber-500/40 font-bold">
                  NO DIRECT FLIGHT
                </span>
              )}
            </div>

            {hasDirectFlight ? (
              <>
                <div className="mb-4">
                  <span className="text-sm font-semibold text-slate-300 block">{outboundDirect.airline}</span>
                  <span className="text-xs font-mono text-slate-400">Flight #{outboundDirect.flight_number}</span>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span className="text-3xl font-black text-white">S${combinedDirectPrice.toFixed(0)}</span>
                    <span className="text-xs text-slate-400">{isRoundTrip ? "SGD Round-Trip" : "SGD One-Way"}</span>
                  </div>
                </div>

                {/* Schedule */}
                <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-800/80 space-y-3 mb-4">
                  <div className="space-y-1">
                    <div className="text-xs font-mono text-cyan-400 font-bold flex justify-between">
                      <span>🛫 Departure: {depDate}</span>
                      <span>S${outboundDirect.price.toFixed(0)}</span>
                    </div>
                    <div className="text-[11px] text-slate-200 font-mono bg-slate-900 p-2 rounded border border-slate-800 flex justify-between items-center">
                      <span className="font-bold text-white">{fmtTime(outboundDirect.legs[0]?.departure_time)} ➔ {fmtTime(outboundDirect.legs[0]?.arrival_time)}</span>
                      <span className="text-cyan-300 font-bold">{outboundDirect.legs[0]?.duration || "7h 30m"}</span>
                    </div>
                    <div className="text-[10px] text-slate-400 font-mono">{outboundDirect.airline} ({outboundDirect.flight_number})</div>
                    <PlatformPriceTable platformPrices={outboundDirect.legs[0]?.platform_prices} cheapestPlatform={outboundDirect.legs[0]?.cheapest_platform} />
                  </div>

                  {isRoundTrip && (
                    <div className="space-y-1 pt-2 border-t border-slate-800">
                      <div className="text-xs font-mono text-indigo-400 font-bold flex justify-between">
                        <span>🛬 Return: {retDate}</span>
                        <span>S${returnDirect.price.toFixed(0)}</span>
                      </div>
                      <div className="text-[11px] text-slate-200 font-mono bg-slate-900 p-2 rounded border border-slate-800 flex justify-between items-center">
                        <span className="font-bold text-white">{fmtTime(returnDirect.legs[0]?.departure_time)} ➔ {fmtTime(returnDirect.legs[0]?.arrival_time)}</span>
                        <span className="text-indigo-300 font-bold">{returnDirect.legs[0]?.duration || "7h 30m"}</span>
                      </div>
                      <div className="text-[10px] text-slate-400 font-mono">{returnDirect.airline} ({returnDirect.flight_number})</div>
                      <PlatformPriceTable platformPrices={returnDirect.legs[0]?.platform_prices} cheapestPlatform={returnDirect.legs[0]?.cheapest_platform} />
                    </div>
                  )}
                </div>
              </>
            ) : (
              <div className="my-6 p-4 bg-amber-950/40 border border-amber-500/30 rounded-xl space-y-2 text-center">
                <div className="text-2xl">🚫</div>
                <div className="text-sm font-bold text-amber-300">No Direct Non-Stop Flight</div>
                <p className="text-xs text-slate-400">
                  No airlines operate direct non-stop flights between <strong className="text-white">{data.origin.code}</strong> and <strong className="text-white">{data.destination.code}</strong>.
                </p>
                <div className="text-[11px] text-cyan-300 font-semibold pt-1">
                  💡 Split routing via transit hubs is required.
                </div>
              </div>
            )}
          </div>
          {hasDirectFlight ? (
            <DealScoreIndicator dealInfo={data.combined_deal_info || outboundDirect.deal_info} currentPrice={combinedDirectPrice} avg60d={data.combined_60d_avg_direct || outboundDirect.avg_60d * 2} avg30d={outboundDirect.avg_30d + returnDirect.avg_30d} />
          ) : (
            <div className="p-3 bg-slate-950/60 rounded-xl border border-slate-800 text-center text-xs text-slate-400">
              Direct Route: <strong className="text-amber-300">N/A</strong>
            </div>
          )}
        </div>

        {/* Card 2: Recommended Split Package */}
        {bestOutboundSplit && (
          <div className="bg-gradient-to-b from-cyan-950/40 via-slate-900/80 to-slate-900/90 border-2 border-cyan-500/60 rounded-2xl p-6 relative flex flex-col justify-between hover:border-cyan-400 transition-all shadow-2xl shadow-cyan-950/50">
            <div className="absolute -top-3 left-6 bg-gradient-to-r from-cyan-500 to-blue-600 text-white text-[11px] font-extrabold px-3.5 py-0.5 rounded-full uppercase tracking-wider shadow-lg">
              ★ Recommended Split Package
            </div>
            <div>
              <div className="flex items-center justify-between mb-4 pt-1">
                <span className="px-3 py-1 bg-cyan-500/20 text-cyan-300 rounded-full text-xs font-bold uppercase tracking-wider border border-cyan-400/40">
                  Via {bestOutboundSplit.hub.city} ({bestOutboundSplit.hub.code})
                </span>
                <span className="text-xs text-emerald-400 font-bold">2-Leg Split</span>
              </div>
              <div className="mb-4">
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-black text-white">S${combinedBestSplitPrice.toFixed(0)}</span>
                  <span className="text-xs text-slate-400">{isRoundTrip ? "SGD Round-Trip" : "SGD One-Way"}</span>
                </div>
                {hasDirectFlight && combinedSavings > 0 ? (
                  <span className="text-xs font-bold text-emerald-400 block mt-1">
                    Save S${combinedSavings.toFixed(0)} vs Direct ({roundPct(combinedSavings, combinedDirectPrice)}% off)
                  </span>
                ) : (
                  <span className="text-xs font-bold text-cyan-300 block mt-1">
                    🌟 Best Value Split Transit Route
                  </span>
                )}
              </div>

              {/* Outbound Split Schedule */}
              <div className="space-y-3.5 mb-4">
                <div className="bg-slate-950/90 p-3.5 rounded-xl border border-cyan-500/40 space-y-2">
                  <div className="flex items-center justify-between text-xs border-b border-cyan-500/20 pb-1.5">
                    <span className="font-mono text-cyan-300 font-extrabold">🛫 OUTBOUND ({depDate})</span>
                    <span className="font-bold text-white">S${bestOutboundSplit.total_price.toFixed(0)}</span>
                  </div>
                  {/* Leg 1 */}
                  <div className="bg-slate-900/90 p-2 rounded text-[11px] font-mono space-y-1">
                    <div className="flex justify-between text-slate-300">
                      <span>LEG 1: {bestOutboundSplit.leg1.origin} ➔ {bestOutboundSplit.leg1.destination} <span className="text-cyan-400 font-normal">({fmtDate(bestOutboundSplit.leg1.departure_date || data.outbound_date)})</span></span>
                      <span className="text-white font-bold">S${bestOutboundSplit.leg1.price.toFixed(0)}</span>
                    </div>
                    <div className="text-slate-400 font-semibold">{bestOutboundSplit.leg1.airline} · {bestOutboundSplit.leg1.flight_number}</div>
                    <div className="flex justify-between text-slate-400">
                      <span>⏰ {fmtTime(bestOutboundSplit.leg1.departure_time)} ➔ {fmtTime(bestOutboundSplit.leg1.arrival_time)}</span>
                      <span>{bestOutboundSplit.leg1.duration}</span>
                    </div>
                    <PlatformPriceTable platformPrices={bestOutboundSplit.leg1.platform_prices} cheapestPlatform={bestOutboundSplit.leg1.cheapest_platform} />
                  </div>
                  {/* Layover */}
                  <div className="text-center py-1 bg-indigo-950/60 border border-indigo-500/30 rounded text-[11px] font-semibold text-indigo-300 font-mono">
                    ⏳ {bestOutboundSplit.layover_duration} at {bestOutboundSplit.hub.city} ({bestOutboundSplit.hub.code})
                  </div>
                  {/* Leg 2 */}
                  <div className="bg-slate-900/90 p-2 rounded text-[11px] font-mono space-y-1">
                    <div className="flex justify-between text-slate-300">
                      <span>LEG 2: {bestOutboundSplit.leg2.origin} ➔ {bestOutboundSplit.leg2.destination} <span className="text-cyan-400 font-normal">({fmtDate(bestOutboundSplit.leg2.departure_date || data.outbound_date)})</span></span>
                      <span className="text-white font-bold">S${bestOutboundSplit.leg2.price.toFixed(0)}</span>
                    </div>
                    <div className="text-slate-400 font-semibold">{bestOutboundSplit.leg2.airline} · {bestOutboundSplit.leg2.flight_number}</div>
                    <div className="flex justify-between text-slate-400">
                      <span>⏰ {fmtTime(bestOutboundSplit.leg2.departure_time)} ➔ {fmtTime(bestOutboundSplit.leg2.arrival_time)}</span>
                      <span>{bestOutboundSplit.leg2.duration}</span>
                    </div>
                    <PlatformPriceTable platformPrices={bestOutboundSplit.leg2.platform_prices} cheapestPlatform={bestOutboundSplit.leg2.cheapest_platform} />
                  </div>
                </div>

                {/* Return Split Schedule */}
                {isRoundTrip && bestReturnSplit && (
                  <div className="bg-slate-950/90 p-3.5 rounded-xl border border-indigo-500/40 space-y-2">
                    <div className="flex items-center justify-between text-xs border-b border-indigo-500/20 pb-1.5">
                      <span className="font-mono text-indigo-300 font-extrabold">🛬 RETURN ({retDate})</span>
                      <span className="font-bold text-white">S${bestReturnSplit.total_price.toFixed(0)}</span>
                    </div>
                    {/* Return Leg 1 */}
                    <div className="bg-slate-900/90 p-2 rounded text-[11px] font-mono space-y-1">
                      <div className="flex justify-between text-slate-300">
                        <span>LEG 1: {bestReturnSplit.leg1.origin} ➔ {bestReturnSplit.leg1.destination} <span className="text-indigo-400 font-normal">({fmtDate(bestReturnSplit.leg1.departure_date || data.return_date)})</span></span>
                        <span className="text-white font-bold">S${bestReturnSplit.leg1.price.toFixed(0)}</span>
                      </div>
                      <div className="text-slate-400 font-semibold">{bestReturnSplit.leg1.airline} · {bestReturnSplit.leg1.flight_number}</div>
                      <div className="flex justify-between text-slate-400">
                        <span>⏰ {fmtTime(bestReturnSplit.leg1.departure_time)} ➔ {fmtTime(bestReturnSplit.leg1.arrival_time)}</span>
                        <span>{bestReturnSplit.leg1.duration}</span>
                      </div>
                      <PlatformPriceTable platformPrices={bestReturnSplit.leg1.platform_prices} cheapestPlatform={bestReturnSplit.leg1.cheapest_platform} />
                    </div>
                    {/* Layover */}
                    <div className="text-center py-1 bg-indigo-950/60 border border-indigo-500/30 rounded text-[11px] font-semibold text-indigo-300 font-mono">
                      ⏳ {bestReturnSplit.layover_duration} at {bestReturnSplit.hub.city} ({bestReturnSplit.hub.code})
                    </div>
                    {/* Return Leg 2 */}
                    <div className="bg-slate-900/90 p-2 rounded text-[11px] font-mono space-y-1">
                      <div className="flex justify-between text-slate-300">
                        <span>LEG 2: {bestReturnSplit.leg2.origin} ➔ {bestReturnSplit.leg2.destination} <span className="text-indigo-400 font-normal">({fmtDate(bestReturnSplit.leg2.departure_date || data.return_date)})</span></span>
                        <span className="text-white font-bold">S${bestReturnSplit.leg2.price.toFixed(0)}</span>
                      </div>
                      <div className="text-slate-400 font-semibold">{bestReturnSplit.leg2.airline} · {bestReturnSplit.leg2.flight_number}</div>
                      <div className="flex justify-between text-slate-400">
                        <span>⏰ {fmtTime(bestReturnSplit.leg2.departure_time)} ➔ {fmtTime(bestReturnSplit.leg2.arrival_time)}</span>
                        <span>{bestReturnSplit.leg2.duration}</span>
                      </div>
                      <PlatformPriceTable platformPrices={bestReturnSplit.leg2.platform_prices} cheapestPlatform={bestReturnSplit.leg2.cheapest_platform} />
                    </div>
                  </div>
                )}
              </div>
            </div>
            <DealScoreIndicator dealInfo={data.combined_deal_info || bestOutboundSplit.deal_info} currentPrice={combinedBestSplitPrice} avg60d={data.combined_60d_avg_split || bestOutboundSplit.avg_60d + (bestReturnSplit?.avg_60d || 0)} avg30d={bestOutboundSplit.avg_30d + (bestReturnSplit?.avg_30d || 0)} />
          </div>
        )}

        {/* Card 3: Moving Average Intelligence */}
        <div className="bg-slate-900/70 border border-slate-800 rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <h4 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
              <span>📈</span> 60-Day Moving Average
            </h4>
            <p className="text-xs text-slate-400 mb-4">Historical pricing averages for departure, return, and combined.</p>
            <div className="space-y-3">
              <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800 flex justify-between items-center">
                <div>
                  <span className="text-xs font-mono text-cyan-300 font-bold block">🛫 Departure ({depDate})</span>
                  <span className="text-[10px] text-slate-400">Direct Avg: {hasDirectFlight ? `S$${outboundDirect.avg_60d.toFixed(0)}` : "N/A"} | Split: S${bestOutboundSplit?.avg_60d?.toFixed(0) || "N/A"}</span>
                </div>
                {bestOutboundSplit && <DealScoreIndicator dealInfo={bestOutboundSplit.deal_info} currentPrice={bestOutboundSplit.total_price} avg60d={bestOutboundSplit.avg_60d} avg30d={bestOutboundSplit.avg_30d} compact />}
              </div>
              {isRoundTrip && (
                <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800 flex justify-between items-center">
                  <div>
                    <span className="text-xs font-mono text-indigo-300 font-bold block">🛬 Return ({retDate})</span>
                    <span className="text-[10px] text-slate-400">Direct Avg: {hasDirectFlight ? `S$${returnDirect.avg_60d.toFixed(0)}` : "N/A"} | Split: S${bestReturnSplit?.avg_60d?.toFixed(0) || "N/A"}</span>
                  </div>
                  {bestReturnSplit && <DealScoreIndicator dealInfo={bestReturnSplit.deal_info} currentPrice={bestReturnSplit.total_price} avg60d={bestReturnSplit.avg_60d} avg30d={bestReturnSplit.avg_30d} compact />}
                </div>
              )}
              {isRoundTrip && (
                <div className="bg-slate-950/90 p-3.5 rounded-xl border border-cyan-500/40 flex justify-between items-center bg-gradient-to-r from-cyan-950/30 to-slate-900">
                  <div>
                    <span className="text-xs font-mono text-white font-extrabold block">🔄 Combined RT 60d Avg</span>
                    <span className="text-[11px] font-bold text-cyan-300">
                      Direct: {hasDirectFlight ? `S$${(outboundDirect.avg_60d + returnDirect.avg_60d).toFixed(0)}` : "N/A"} | Split: S$${((bestOutboundSplit?.avg_60d || 0) + (bestReturnSplit?.avg_60d || 0)).toFixed(0)}
                    </span>
                  </div>
                  <DealScoreIndicator dealInfo={data.combined_deal_info || outboundDirect.deal_info} currentPrice={combinedBestSplitPrice} avg60d={(bestOutboundSplit?.avg_60d || 0) + (bestReturnSplit?.avg_60d || 0)} avg30d={(bestOutboundSplit?.avg_30d || 0) + (bestReturnSplit?.avg_30d || 0)} compact />
                </div>
              )}
            </div>
          </div>
          <div className="pt-4 border-t border-slate-800">
            <span className="text-[11px] text-slate-500 block text-center">SQLite pricing engine tracking trends across {outboundSplits.length} transit hubs.</span>
          </div>
        </div>
      </div>

      {/* Route Matrix Table */}
      <div className="bg-slate-900/70 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
        <div className="p-4 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between">
          <h4 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <span>📊</span> Route Comparison Matrix
          </h4>
          <span className="text-xs text-slate-400">Click row to highlight hub on map</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
              <tr>
                <th className="py-3.5 px-4">Hub</th>
                <th className="py-3.5 px-4">🛫 Outbound ({depDate})</th>
                {isRoundTrip && <th className="py-3.5 px-4">🛬 Return ({retDate})</th>}
                <th className="py-3.5 px-4">Total</th>
                <th className="py-3.5 px-4">Savings</th>
                <th className="py-3.5 px-4">Deal</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-medium">
              {/* Direct row */}
              <tr className="bg-slate-950/40 hover:bg-slate-900/50 transition-colors">
                <td className="py-3.5 px-4">
                  <span className="px-2.5 py-1 bg-slate-800 text-slate-200 rounded text-[11px] font-extrabold uppercase border border-slate-700">DIRECT</span>
                </td>
                <td className="py-3.5 px-4 font-mono text-slate-200">
                  {hasDirectFlight ? (
                    <>
                      <div className="font-bold text-white">{data.origin.code} ➔ {data.destination.code} (S${outboundDirect.price.toFixed(0)})</div>
                      <div className="text-[11px] text-cyan-300 mt-1 bg-slate-900 p-1.5 rounded border border-slate-800">
                        📅 {depDate} · {fmtTime(outboundDirect.legs[0]?.departure_time)} ➔ {fmtTime(outboundDirect.legs[0]?.arrival_time)} ({outboundDirect.legs[0]?.duration || "7h 30m"})
                      </div>
                      <div className="text-[10px] text-slate-400 mt-0.5">{outboundDirect.airline} #{outboundDirect.flight_number}</div>
                    </>
                  ) : (
                    <div className="text-amber-400 font-semibold italic text-xs">
                      🚫 No Direct Non-Stop Operating
                    </div>
                  )}
                </td>
                {isRoundTrip && (
                  <td className="py-3.5 px-4 font-mono text-slate-200">
                    {hasDirectFlight ? (
                      <>
                        <div className="font-bold text-white">{data.destination.code} ➔ {data.origin.code} (S${returnDirect.price.toFixed(0)})</div>
                        <div className="text-[11px] text-indigo-300 mt-1 bg-slate-900 p-1.5 rounded border border-slate-800">
                          📅 {retDate} · {fmtTime(returnDirect.legs[0]?.departure_time)} ➔ {fmtTime(returnDirect.legs[0]?.arrival_time)} ({returnDirect.legs[0]?.duration || "7h 30m"})
                        </div>
                        <div className="text-[10px] text-slate-400 mt-0.5">{returnDirect.airline} #{returnDirect.flight_number}</div>
                      </>
                    ) : (
                      <div className="text-amber-400 font-semibold italic text-xs">
                        🚫 No Direct Non-Stop Operating
                      </div>
                    )}
                  </td>
                )}
                <td className="py-3.5 px-4 font-extrabold text-white text-sm">
                  {hasDirectFlight ? `S$${combinedDirectPrice.toFixed(0)}` : "N/A"}
                </td>
                <td className="py-3.5 px-4 text-slate-500">— Benchmark —</td>
                <td className="py-3.5 px-4">
                  {hasDirectFlight ? (
                    <DealScoreIndicator dealInfo={outboundDirect.deal_info} currentPrice={combinedDirectPrice} avg60d={outboundDirect.avg_60d} avg30d={outboundDirect.avg_30d} compact />
                  ) : (
                    <span className="text-amber-400 font-bold text-[11px]">N/A</span>
                  )}
                </td>
              </tr>

              {/* Split rows */}
              {outboundSplits.map((optOut, i) => {
                const optRet = returnSplits[i] || optOut;
                const pkgPrice = isRoundTrip ? optOut.total_price + optRet.total_price : optOut.total_price;
                const benchmark = isRoundTrip ? combinedDirectPrice : outboundDirect.price;
                const savings = hasDirectFlight ? (benchmark - pkgPrice) : 0;
                const isSelected = selectedHub === optOut.hub.code;

                return (
                  <tr key={i} onClick={() => onSelectHub?.(optOut.hub.code)}
                    className={`transition-colors cursor-pointer ${
                      isSelected ? "bg-indigo-950/60 ring-2 ring-indigo-500/80"
                        : optOut.is_best_split ? "bg-cyan-950/30 hover:bg-cyan-900/40"
                        : "hover:bg-slate-800/40"
                    }`}>
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2">
                        <span className="font-extrabold text-cyan-300">{optOut.hub.code}</span>
                        <span className="text-slate-400 text-[11px]">({optOut.hub.city})</span>
                        {optOut.is_best_split && <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-1.5 py-0.5 rounded font-extrabold border border-emerald-500/30">BEST</span>}
                      </div>
                      <div className="text-[10px] text-indigo-300 mt-1 font-mono">⏳ {optOut.layover_duration}</div>
                    </td>
                    <td className="py-3.5 px-4 font-mono">
                      <div className="text-[11px] text-cyan-300 font-bold">📅 {depDate}</div>
                      <div className="text-[11px] text-slate-200 mt-0.5">
                        {optOut.leg1.origin}➔{optOut.leg1.destination}: {fmtTime(optOut.leg1.departure_time)} ➔ {fmtTime(optOut.leg1.arrival_time)} ({optOut.leg1.duration})
                      </div>
                      <div className="text-[10px] text-indigo-300 my-0.5">⏳ {optOut.layover_duration}</div>
                      <div className="text-[11px] text-slate-200">
                        {optOut.leg2.origin}➔{optOut.leg2.destination}: {fmtTime(optOut.leg2.departure_time)} ➔ {fmtTime(optOut.leg2.arrival_time)} ({optOut.leg2.duration})
                      </div>
                    </td>
                    {isRoundTrip && (
                      <td className="py-3.5 px-4 font-mono">
                        <div className="text-[11px] text-indigo-300 font-bold">📅 {retDate}</div>
                        <div className="text-[11px] text-slate-200 mt-0.5">
                          {optRet.leg1.origin}➔{optRet.leg1.destination}: {fmtTime(optRet.leg1.departure_time)} ➔ {fmtTime(optRet.leg1.arrival_time)} ({optRet.leg1.duration})
                        </div>
                        <div className="text-[10px] text-indigo-300 my-0.5">⏳ {optRet.layover_duration}</div>
                        <div className="text-[11px] text-slate-200">
                          {optRet.leg2.origin}➔{optRet.leg2.destination}: {fmtTime(optRet.leg2.departure_time)} ➔ {fmtTime(optRet.leg2.arrival_time)} ({optRet.leg2.duration})
                        </div>
                      </td>
                    )}
                    <td className="py-3.5 px-4 font-black text-white text-base">S${pkgPrice.toFixed(0)}</td>
                    <td className="py-3.5 px-4">
                      {hasDirectFlight ? (
                        savings > 0 ? (
                          <span className="text-emerald-400 font-extrabold text-xs">Save S${savings.toFixed(0)} ({roundPct(savings, benchmark)}%)</span>
                        ) : (
                          <span className="text-slate-500 text-xs">+S${Math.abs(savings).toFixed(0)} more</span>
                        )
                      ) : (
                        <span className="text-cyan-300 font-extrabold text-xs">🌟 Required Split</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4">
                      <DealScoreIndicator dealInfo={optOut.deal_info} currentPrice={pkgPrice} avg60d={optOut.avg_60d + optRet.avg_60d} avg30d={optOut.avg_30d + optRet.avg_30d} compact />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function roundPct(part: number, total: number): number {
  if (total <= 0) return 0;
  return Math.round((part / total) * 100);
}
