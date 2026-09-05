"use client";

import React from "react";
import { DealInfo } from "@/types/flight";

interface Props {
  dealInfo: DealInfo;
  currentPrice: number;
  avg60d: number;
  avg30d: number;
  compact?: boolean;
}

export default function DealScoreIndicator({
  dealInfo,
  currentPrice,
  avg60d,
  avg30d,
  compact = false,
}: Props) {
  const isGreen = dealInfo.tier === "green";
  const isYellow = dealInfo.tier === "yellow";

  // Calculate percentage fill relative to average
  const maxScale = Math.max(avg60d * 1.3, currentPrice * 1.1);
  const currentPct = Math.min(100, Math.max(10, (currentPrice / maxScale) * 100));
  const avg60dPct = Math.min(100, Math.max(10, (avg60d / maxScale) * 100));

  if (compact) {
    return (
      <span
        className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-extrabold backdrop-blur-md transition-all border ${
          isGreen
            ? "bg-emerald-500/25 text-emerald-300 border-emerald-500/50 shadow-lg shadow-emerald-950/40"
            : isYellow
            ? "bg-amber-500/25 text-amber-300 border-amber-500/50"
            : "bg-slate-700/50 text-slate-200 border-slate-600/50"
        }`}
      >
        {dealInfo.badge}
      </span>
    );
  }

  return (
    <div
      className={`p-5 rounded-2xl border backdrop-blur-md transition-all ${
        isGreen
          ? "bg-emerald-950/40 border-emerald-500/50 shadow-xl shadow-emerald-950/40"
          : isYellow
          ? "bg-amber-950/30 border-amber-500/40"
          : "bg-slate-900/50 border-slate-800"
      }`}
    >
      <div className="flex items-center justify-between mb-3.5">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`px-3.5 py-1.5 rounded-full text-xs font-black uppercase tracking-wider border ${
              isGreen
                ? "bg-emerald-500/25 text-emerald-300 border-emerald-400/60 animate-pulse"
                : isYellow
                ? "bg-amber-500/25 text-amber-300 border-amber-400/60"
                : "bg-rose-500/25 text-rose-300 border-rose-400/60"
            }`}
          >
            {dealInfo.badge}
          </span>
          {dealInfo.is_great_deal && (
            <span className="text-xs font-black text-emerald-400 uppercase tracking-wider bg-emerald-950/90 px-2.5 py-1 rounded-lg border border-emerald-500/60">
              ≥20% DROP DETECTED
            </span>
          )}
        </div>
        <div className="text-right">
          <span className="text-3xl font-black text-white">S${currentPrice.toFixed(0)}</span>
          <span className="text-xs text-slate-400 ml-1 font-bold">SGD</span>
        </div>
      </div>

      <p className="text-sm font-semibold text-slate-200 mb-3.5">{dealInfo.message}</p>

      {/* Moving Average Visual Comparison Bar */}
      <div className="space-y-2 pt-1">
        <div className="flex justify-between text-xs font-medium text-slate-300">
          <span>Current: <strong className="text-white font-bold">S${currentPrice.toFixed(0)}</strong></span>
          <span>60d Avg: <strong className="text-cyan-300 font-bold">S${avg60d.toFixed(0)}</strong></span>
          <span>30d Avg: <strong className="text-indigo-300 font-bold">S${avg30d.toFixed(0)}</strong></span>
        </div>

        <div className="relative h-3 w-full bg-slate-800 rounded-full overflow-hidden border border-slate-700/60">
          {/* 60d average benchmark tick */}
          <div
            className="absolute top-0 bottom-0 w-1.5 bg-cyan-400 z-10 shadow-sm shadow-cyan-400"
            style={{ left: `${avg60dPct}%` }}
            title={`60-day Moving Avg: S$${avg60d}`}
          />
          {/* Current price bar */}
          <div
            className={`h-full rounded-full transition-all duration-700 ${
              isGreen
                ? "bg-gradient-to-r from-emerald-500 to-teal-400"
                : isYellow
                ? "bg-gradient-to-r from-amber-500 to-yellow-400"
                : "bg-gradient-to-r from-rose-500 to-red-400"
            }`}
            style={{ width: `${currentPct}%` }}
          />
        </div>
      </div>
    </div>
  );
}
