import { useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  GeoJSON,
  ImageOverlay,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { heatmapUrl } from "../api";

const INDIA_CENTER = [22.9734, 78.6569];
const INDIA_ZOOM = 5;

function bboxToBounds(bbox) {
  // bbox = [lon_min, lat_min, lon_max, lat_max]
  const [lonMin, latMin, lonMax, latMax] = bbox;
  return [
    [latMin, lonMin],
    [latMax, lonMax],
  ];
}

function FlyToRegion({ bbox }) {
  const map = useMap();
  useEffect(() => {
    if (bbox) {
      map.flyToBounds(bboxToBounds(bbox), { padding: [40, 40], duration: 1.1 });
    } else {
      map.flyTo(INDIA_CENTER, INDIA_ZOOM, { duration: 1.1 });
    }
  }, [bbox, map]);
  return null;
}

const changeStyle = (feature) => {
  const category = feature.properties.change_category;
  const colors = {
    construction: "#ff5a1f",
    vegetation_loss: "#e63946",
    vegetation_gain: "#52b788",
    water_body_change: "#4cc9f0",
    general_change: "#ff9933",
  };
  return {
    color: colors[category] || "#ff9933",
    weight: 2,
    fillColor: colors[category] || "#ff9933",
    fillOpacity: 0.35,
  };
};

function onEachFeature(feature, layer) {
  const p = feature.properties;
  const categoryLabel = (p.change_category || "unknown").replace(/_/g, " ");
  layer.bindPopup(`
    <div class="geojson-popup">
      <strong>${categoryLabel}</strong><br/>
      Confidence: <b>${p.confidence_pct}%</b><br/>
      Area: ${p.area_km2} km²<br/>
      NDVI Δ: ${Number(p.ndvi_delta).toFixed(4)}
    </div>
  `);
}

export default function MapView({ bbox, geojson, region, showHeatmap }) {
  return (
    <div className="map-card">
      <div className="map-card__header">
        <h2>Change Overlay Map</h2>
      </div>
      <div className="map-card__container">
        <MapContainer
          center={INDIA_CENTER}
          zoom={INDIA_ZOOM}
          scrollWheelZoom
          style={{ height: "100%", width: "100%" }}
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; OpenStreetMap contributors'
          />
          <FlyToRegion bbox={bbox} />
          {showHeatmap && bbox && (
            <ImageOverlay
              url={heatmapUrl(region)}
              bounds={bboxToBounds(bbox)}
              opacity={0.65}
            />
          )}
          {geojson && (
            <GeoJSON
              key={region + (showHeatmap ? "-hm" : "-nohm")}
              data={geojson}
              style={changeStyle}
              onEachFeature={onEachFeature}
            />
          )}
        </MapContainer>
      </div>
    </div>
  );
}
