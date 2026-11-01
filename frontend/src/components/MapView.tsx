import 'leaflet/dist/leaflet.css';
import { useEffect } from 'react';
import { CircleMarker, MapContainer, Polyline, Popup, TileLayer, Tooltip, useMap, useMapEvents } from 'react-leaflet';
import type { LatLngBoundsExpression, LatLngExpression } from 'leaflet';

// Se usan CircleMarker (vectoriales) en vez de Marker para no depender de las
// imágenes PNG de Leaflet, que Vite no resuelve sin configuración extra.

export interface MapPoint {
  id: number | string;
  lat: number;
  lng: number;
  color: string;
  label?: string;
  popup?: React.ReactNode;
  sequence?: number;
}

function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap();
  // Clave estable: solo se reencuadra si cambian las coordenadas, no en cada render.
  const key = JSON.stringify(points);
  useEffect(() => {
    const pts = JSON.parse(key) as [number, number][];
    if (pts.length > 1) map.fitBounds(pts as LatLngBoundsExpression, { padding: [30, 30], maxZoom: 15 });
    else if (pts.length === 1) map.setView(pts[0], 14);
  }, [map, key]);
  return null;
}

function ClickHandler({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  useMapEvents({ click: (e) => onPick(Number(e.latlng.lat.toFixed(6)), Number(e.latlng.lng.toFixed(6))) });
  return null;
}

export function MapView({
  points,
  depot,
  path,
  height = 380,
  onPick,
}: {
  points: MapPoint[];
  depot?: { lat: number; lng: number };
  path?: [number, number][];
  height?: number;
  onPick?: (lat: number, lng: number) => void;
}) {
  const center: LatLngExpression = depot ? [depot.lat, depot.lng] : [-12.0464, -77.0428];
  const bounds: [number, number][] = [...points.map((p) => [p.lat, p.lng] as [number, number]), ...(depot ? [[depot.lat, depot.lng] as [number, number]] : [])];
  return (
    <div style={{ height }} className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800">
      <MapContainer center={center} zoom={12} scrollWheelZoom className="h-full w-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {path && path.length > 1 && <Polyline positions={path} pathOptions={{ color: '#1d5ef1', weight: 4, opacity: 0.7, dashArray: '6 6' }} />}
        {depot && (
          <CircleMarker center={[depot.lat, depot.lng]} radius={10} pathOptions={{ color: '#0f172a', fillColor: '#facc15', fillOpacity: 1, weight: 2 }}>
            <Tooltip direction="top">Depósito central</Tooltip>
          </CircleMarker>
        )}
        {points.map((p) => (
          <CircleMarker key={p.id} center={[p.lat, p.lng]} radius={p.sequence ? 9 : 7} pathOptions={{ color: '#fff', weight: 2, fillColor: p.color, fillOpacity: 0.95 }}>
            {(p.label || p.sequence) && (
              <Tooltip direction="top" permanent={!!p.sequence} className="!px-1.5 !py-0 !text-xs !font-semibold">
                {p.sequence ?? p.label}
              </Tooltip>
            )}
            {p.popup && <Popup>{p.popup}</Popup>}
          </CircleMarker>
        ))}
        {onPick && <ClickHandler onPick={onPick} />}
        <FitBounds points={bounds} />
      </MapContainer>
    </div>
  );
}

export default MapView;
