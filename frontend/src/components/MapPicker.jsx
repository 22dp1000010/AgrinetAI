import { MapContainer, TileLayer, CircleMarker, useMapEvents } from 'react-leaflet'

function ClickHandler({ onPick }) {
  useMapEvents({ click: (e) => onPick([e.latlng.lat, e.latlng.lng]) })
  return null
}

export default function MapPicker({ position, onPick }) {
  return (
    <MapContainer
      center={position}
      zoom={8}
      className="h-56 w-full rounded-xl z-0"
      scrollWheelZoom={false}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ClickHandler onPick={onPick} />
      <CircleMarker
        center={position}
        radius={10}
        pathOptions={{ color: '#047857', fillColor: '#10b981', fillOpacity: 0.8 }}
      />
    </MapContainer>
  )
}
