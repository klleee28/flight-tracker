"use client";

import React from "react";

const PLATFORM_ICONS: Record<string, string> = {
  "Google Flights": "🔵",
  "Trip.com":       "🟢",
  "Booking.com":    "🟡",
  "Agoda":          "🔴",
  "Official Airline Direct": "✈️",
};

function getPlatformIcon(platform: string): string {
  if (PLATFORM_ICONS[platform]) return PLATFORM_ICONS[platform];
  if (platform.includes(".com") || platform.includes(".co") || platform.includes(".net") || platform.includes("Airline") || platform.includes("Official")) {
    return "✈️";
  }
  return "🌐";
}

interface Props {
  platformPrices?: Record<string, number>;
  cheapestPlatform?: string;
  compact?: boolean;
}

export default function PlatformPriceTable({ platformPrices, cheapestPlatform, compact = false }: Props) {
  if (!platformPrices || Object.keys(platformPrices).length === 0) return null;

  const entries = Object.entries(platformPrices).sort((a, b) => a[1] - b[1]);

  if (compact) {
    return (
      <div className="flex flex-wrap gap-1.5 mt-2">
        {entries.map(([platform, price]) => {
          const isCheapest = platform === cheapestPlatform;
          return (
            <span
              key={platform}
              title={platform}
              className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-bold font-mono border transition-all ${
                isCheapest
                  ? "bg-emerald-500/25 text-emerald-300 border-emerald-500/50 shadow-sm"
                  : "bg-slate-800 text-slate-300 border-slate-700"
              }`}
            >
              <span>{getPlatformIcon(platform)}</span>
              <span className="hidden sm:inline">{platform.split(" ")[0]}</span>
              <span>S${price.toFixed(0)}</span>
              {isCheapest && <span className="text-emerald-400 font-extrabold">✓</span>}
            </span>
          );
        })}
      </div>
    );
  }

  return (
    <div className="mt-2.5 rounded-xl overflow-hidden border border-slate-700/80">
      <div className="px-3 py-1.5 bg-slate-800/90 text-xs font-black uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
        <span>🌐</span> Platform Price Breakdown
      </div>
      <div className="divide-y divide-slate-800/80">
        {entries.map(([platform, price], idx) => {
          const isCheapest = platform === cheapestPlatform;
          const priceDiff = price - entries[0][1];
          return (
            <div
              key={platform}
              className={`flex items-center justify-between px-3 py-2 text-xs font-mono transition-all ${
                isCheapest
                  ? "bg-emerald-950/50"
                  : idx % 2 === 0
                  ? "bg-slate-900/70"
                  : "bg-slate-950/70"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="text-sm">{getPlatformIcon(platform)}</span>
                <span className={isCheapest ? "text-emerald-300 font-extrabold" : "text-slate-200 font-medium"}>
                  {platform}
                </span>
                {isCheapest && (
                  <span className="text-[10px] bg-emerald-500/25 text-emerald-300 px-1.5 py-0.5 rounded font-black border border-emerald-500/40 uppercase">
                    Cheapest
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <span className={`font-black text-sm ${isCheapest ? "text-emerald-300" : "text-white"}`}>
                  S${price.toFixed(0)}
                </span>
                {priceDiff > 0 && (
                  <span className="text-slate-400 text-xs">+S${priceDiff.toFixed(0)}</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
