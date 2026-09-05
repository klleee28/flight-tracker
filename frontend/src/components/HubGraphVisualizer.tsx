"use client";

import React from "react";
import dynamic from "next/dynamic";

// Dynamically import LeafletMap with SSR disabled (Leaflet requires window)
const LeafletMap = dynamic(() => import("./LeafletMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-slate-950 flex items-center justify-center text-xs text-slate-400 font-mono">
      <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping mr-2" />
      Loading High-Definition Asian Flight Map Tiles...
    </div>
  ),
});

interface Props {
  activeOrigin?: string;
  activeDestination?: string;
  activeHub?: string;
  onSelectHub?: (hubCode: string) => void;
}

export default function HubGraphVisualizer({
  activeOrigin = "BWN",
  activeDestination = "CTS",
  activeHub = "KUL",
  onSelectHub,
}: Props) {
  return (
    <div className="w-full bg-slate-900/80 border border-slate-800 rounded-2xl p-6 backdrop-blur-xl shadow-2xl relative overflow-hidden">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4 z-10 relative">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-ping" />
            <h3 className="text-lg font-black text-white tracking-wide uppercase flex items-center gap-2">
              <span>🌏</span> Interactive Asian Transit Hub Map (Scroll & Zoom)
            </h3>
          </div>
          <p className="text-sm font-semibold text-slate-300 mt-1">
            Real-world GPS coordinates with interactive panning, scroll-zoom, and curved flight arcs.
          </p>
        </div>

        {/* Dynamic Route Legend */}
        <div className="flex flex-wrap items-center gap-3 text-sm font-bold">
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-cyan-950/80 border border-cyan-500/50 text-cyan-300">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-sm shadow-cyan-400" />
            Origin: {activeOrigin}
          </span>
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-indigo-950/80 border border-indigo-500/50 text-indigo-300">
            <span className="w-2.5 h-2.5 rounded-full bg-indigo-400 shadow-sm shadow-indigo-400" />
            Active Hub: {activeHub}
          </span>
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-950/80 border border-emerald-500/50 text-emerald-300">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400" />
            Destination: {activeDestination}
          </span>
        </div>
      </div>

      {/* Interactive Scrollable Leaflet Map Container */}
      <div className="relative w-full h-[420px] bg-slate-950 rounded-xl border border-slate-800/90 overflow-hidden shadow-2xl">
        <LeafletMap
          activeOrigin={activeOrigin}
          activeDestination={activeDestination}
          activeHub={activeHub}
          onSelectHub={onSelectHub}
        />
      </div>

      <div className="mt-3 flex items-center justify-between text-xs text-slate-300 font-mono font-semibold">
        <span>💡 Use mouse wheel / pinch gestures to zoom & drag map freely</span>
        <span>CartoDB Dark Matter GPS Map v2.0</span>
      </div>
    </div>
  );
}
