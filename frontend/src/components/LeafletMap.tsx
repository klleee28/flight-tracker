"use client";

import React, { useEffect } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

interface AirportGPS {
  code: string;
  name: string;
  city: string;
  country: string;
  flag: string;
  lat: number;
  lng: number;
}

const AIRPORTS_GPS: Record<string, AirportGPS> = {
  BWN: { code: "BWN", name: "Brunei International", city: "Bandar Seri Begawan", country: "Brunei", flag: "🇧🇳", lat: 4.9442, lng: 114.9283 },
  CTS: { code: "CTS", name: "New Chitose Airport", city: "Sapporo", country: "Japan", flag: "🇯🇵", lat: 42.7752, lng: 141.6923 },
  KUL: { code: "KUL", name: "Kuala Lumpur Intl", city: "Kuala Lumpur", country: "Malaysia", flag: "🇲🇾", lat: 2.7456, lng: 101.7099 },
  SIN: { code: "SIN", name: "Singapore Changi", city: "Singapore", country: "Singapore", flag: "🇸🇬", lat: 1.3644, lng: 103.9915 },
  MNL: { code: "MNL", name: "Ninoy Aquino Intl", city: "Manila", country: "Philippines", flag: "🇵🇭", lat: 14.5086, lng: 121.0194 },
  TPE: { code: "TPE", name: "Taoyuan Intl", city: "Taipei", country: "Taiwan", flag: "🇹🇼", lat: 25.0797, lng: 121.2342 },
  HKG: { code: "HKG", name: "Hong Kong Intl", city: "Hong Kong", country: "Hong Kong", flag: "🇭🇰", lat: 22.3080, lng: 113.9185 },
  BKK: { code: "BKK", name: "Suvarnabhumi", city: "Bangkok", country: "Thailand", flag: "🇹🇭", lat: 13.6900, lng: 100.7501 },
  NRT: { code: "NRT", name: "Narita International", city: "Tokyo", country: "Japan", flag: "🇯🇵", lat: 35.7720, lng: 140.3929 },
  ICN: { code: "ICN", name: "Incheon International", city: "Seoul", country: "South Korea", flag: "🇰🇷", lat: 37.4602, lng: 126.4407 },
  DPS: { code: "DPS", name: "Ngurah Rai", city: "Bali", country: "Indonesia", flag: "🇮🇩", lat: -8.7482, lng: 115.1672 },
};

interface Props {
  activeOrigin?: string;
  activeDestination?: string;
  activeHub?: string;
  onSelectHub?: (hubCode: string) => void;
}

// Generate quadratic Bezier flight curve points between two GPS locations
function generateCurvedPoints(
  start: [number, number],
  end: [number, number],
  numPoints: number = 30
): [number, number][] {
  const [lat1, lng1] = start;
  const [lat2, lng2] = end;

  const midLat = (lat1 + lat2) / 2;
  const midLng = (lng1 + lng2) / 2;

  // Perpendicular curve offset
  const dLat = lat2 - lat1;
  const dLng = lng2 - lng1;

  const controlLat = midLat + dLng * 0.18;
  const controlLng = midLng - dLat * 0.18;

  const points: [number, number][] = [];
  for (let i = 0; i <= numPoints; i++) {
    const t = i / numPoints;
    const lat = (1 - t) * (1 - t) * lat1 + 2 * (1 - t) * t * controlLat + t * t * lat2;
    const lng = (1 - t) * (1 - t) * lng1 + 2 * (1 - t) * t * controlLng + t * t * lng2;
    points.push([lat, lng]);
  }
  return points;
}

// Map bounds controller to auto-fit search route
function MapController({ origin, dest, hub }: { origin: AirportGPS; dest: AirportGPS; hub: AirportGPS }) {
  const map = useMap();
  useEffect(() => {
    const bounds = L.latLngBounds([
      [origin.lat, origin.lng],
      [dest.lat, dest.lng],
      [hub.lat, hub.lng],
    ]);
    map.fitBounds(bounds, { padding: [50, 50], maxZoom: 6 });
  }, [origin, dest, hub, map]);
  return null;
}

export default function LeafletMap({
  activeOrigin = "BWN",
  activeDestination = "CTS",
  activeHub = "KUL",
  onSelectHub,
}: Props) {
  const orig = AIRPORTS_GPS[activeOrigin] || AIRPORTS_GPS["BWN"];
  const dest = AIRPORTS_GPS[activeDestination] || AIRPORTS_GPS["CTS"];
  const hub = AIRPORTS_GPS[activeHub] || AIRPORTS_GPS["KUL"];

  const leg1Curve = generateCurvedPoints([orig.lat, orig.lng], [hub.lat, hub.lng]);
  const leg2Curve = generateCurvedPoints([hub.lat, hub.lng], [dest.lat, dest.lng]);
  const directCurve = generateCurvedPoints([orig.lat, orig.lng], [dest.lat, dest.lng]);

  const createCustomIcon = (code: string, flag: string, isOrigin: boolean, isDest: boolean, isHub: boolean) => {
    const bgClass = isOrigin
      ? "bg-cyan-500 text-slate-950 border-white ring-4 ring-cyan-500/50"
      : isDest
      ? "bg-emerald-500 text-slate-950 border-white ring-4 ring-emerald-500/50"
      : isHub
      ? "bg-indigo-600 text-white border-indigo-300 ring-4 ring-indigo-500/50"
      : "bg-slate-900/90 text-slate-200 border-slate-700 hover:border-cyan-400";

    const html = `
      <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-bold shadow-2xl ${bgClass}">
        <span>${flag}</span>
        <span class="font-mono font-extrabold">${code}</span>
        ${isHub ? '<span class="text-[9px] bg-indigo-950 text-cyan-300 px-1 rounded font-mono">HUB</span>' : ""}
      </div>
    `;

    return L.divIcon({
      html,
      className: "custom-leaflet-marker",
      iconSize: [80, 30],
      iconAnchor: [40, 15],
    });
  };

  return (
    <div className="w-full h-full relative">
      <MapContainer
        center={[20.0, 120.0]}
        zoom={4}
        scrollWheelZoom={true}
        className="w-full h-full bg-slate-950 z-0 rounded-xl"
        style={{ height: "100%", width: "100%" }}
      >
        <MapController origin={orig} dest={dest} hub={hub} />

        {/* 100% Free Esri World Dark Gray Canvas Map Tiles (Zero API key required) */}
        <TileLayer
          attribution='&copy; <a href="https://www.esri.com/">Esri</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
          maxZoom={16}
        />

        {/* Direct Baseline Flight Arc */}
        <Polyline
          positions={directCurve}
          pathOptions={{ color: "#f43f5e", weight: 2, dashArray: "5, 8", opacity: 0.4 }}
        />

        {/* Leg 1 Arc: Origin -> Hub (Cyan Arc) */}
        <Polyline
          positions={leg1Curve}
          pathOptions={{ color: "#06b6d4", weight: 4, opacity: 0.95 }}
        />

        {/* Leg 2 Arc: Hub -> Destination (Emerald Arc) */}
        <Polyline
          positions={leg2Curve}
          pathOptions={{ color: "#10b981", weight: 4, opacity: 0.95 }}
        />

        {/* Airport Markers at exact GPS Locations */}
        {Object.values(AIRPORTS_GPS).map((ap) => {
          const isOrigin = ap.code === orig.code;
          const isDest = ap.code === dest.code;
          const isHub = ap.code === hub.code;

          return (
            <Marker
              key={ap.code}
              position={[ap.lat, ap.lng]}
              icon={createCustomIcon(ap.code, ap.flag, isOrigin, isDest, isHub)}
              eventHandlers={{
                click: () => onSelectHub && onSelectHub(ap.code),
              }}
            >
              <Popup className="custom-leaflet-popup">
                <div className="p-1 text-slate-900 font-sans">
                  <div className="font-bold text-xs">
                    {ap.flag} {ap.name} ({ap.code})
                  </div>
                  <div className="text-[11px] text-slate-600">
                    {ap.city}, {ap.country}
                  </div>
                  <div className="text-[10px] text-indigo-600 font-mono mt-1">
                    GPS: {ap.lat.toFixed(4)}°N, {ap.lng.toFixed(4)}°E
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>
    </div>
  );
}
