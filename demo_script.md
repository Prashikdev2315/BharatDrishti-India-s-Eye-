# BharatDrishti — Demo Video Script
# Duration: 3:45 | Track: Sovereign Technology for India

---

## Segment 1 — Hook (0:00–0:30)

**[SCREEN]** Black screen. Text fades in: *"India. 3.29 million km². 290 TB of satellite data. Every day."*
Then: *"Who is watching?"*

**[WORDS]**
Every day, Sentinel-2 satellites pass over every corner of India — from the Ladakh border to the Navi Mumbai coast to the Brahmaputra floodplains. They capture everything: new construction, flood events, deforestation, road expansion. 290 terabytes of raw intelligence. And almost none of it gets analysed in time to matter. Today we show you how India watches itself.

---

## Segment 2 — Problem (0:30–1:00)

**[SCREEN]** Split screen: Google Earth Engine logo on left, Planet Labs logo on right. Red X appears over both. Then text: *"Foreign-controlled. Subscription-gated. No offline mode."*

**[WORDS]**
The tools that exist today — Google Earth Engine, Planet Labs — are American-controlled, subscription-gated platforms. If India's border monitoring or disaster response depends on a US company's API staying online, that is not sovereignty. That is dependency. There is no Indian-built, AI-powered, offline-capable system for monitoring land-cover change across Indian territory — until now.

---

## Segment 3 — Solution (1:00–1:30)

**[SCREEN]** Show BharatDrishti dashboard loading. Title card appears: *"BharatDrishti — India's Eye"*. Brief code flash of `inference.py` showing `ChangeFormerV6`. Then architecture diagram: 4 boxes — Sentinel-2 → ChangeFormerV6 → FastAPI → React/Leaflet.

**[WORDS]**
BharatDrishti — India's Eye — is an end-to-end sovereign satellite intelligence platform. It ingests free Copernicus Sentinel-2 satellite data, runs it through ChangeFormerV6 — a Siamese Transformer AI model with 41 million parameters, achieving 94.95% accuracy on change detection benchmarks — and delivers actionable intelligence: change heatmaps, GeoJSON polygons, NDVI vegetation maps, and an automated AI analysis brief. It runs 100% offline on Indian infrastructure. No foreign API. No subscription.

---

## Segment 4 — Navi Mumbai Demo (1:30–2:15)

**[SCREEN]** Click "Navi Mumbai" region card in sidebar. Loading spinner. Results populate. Pan to Leaflet map showing red change polygons over coastal area. Drag the before/after compare slider from right to left slowly. Click the largest polygon — popup appears showing: confidence, area, category, NDVI delta.

**[WORDS]**
We select Navi Mumbai — a full year of change, January 2023 to January 2024. The system processes the bi-temporal Sentinel-2 imagery and returns 39 detected change polygons, covering 297.71 square kilometres — 46.9% of the monitored area. Watch the before-after slider: this is January 2023, mostly tidal mudflat and open ground. This is January 2024 — entire construction zones have emerged. We click a polygon: 12.4 km², confidence 51%, category: construction, NDVI delta minus 0.18. That NDVI drop — near-infrared falling, red rising — is the spectral signature of bare soil replacing vegetation. Classic construction pattern.

---

## Segment 5 — Assam/Bihar (2:15–2:45)

**[SCREEN]** Click "Assam/Bihar" in sidebar. Map recentres to northeastern India. Three large blue polygons visible. Show stats panel: 3 polygons, 12.2 km², water_body_change category. Show NDVI diff panel — green-to-red legend visible.

**[WORDS]**
Assam and Bihar — India's flood belt. We compare May 2024 to September 2024, straddling the monsoon peak. Three change polygons, total 12.2 km². Category: water body change. The NDVI difference map confirms it — the red zones mark areas where standing water replaced vegetation during the flood event. Three polygons because flood inundation is spatially contiguous — not fragmented. Each polygon here represents thousands of affected families. This is the kind of rapid environmental monitoring that NDMA needs in real time.

---

## Segment 6 — Ladakh (2:45–3:15)

**[SCREEN]** Click "Ladakh" in sidebar. Map recentres to high-altitude terrain. Two compact polygons visible on mountain terrain. Stats: 2 polygons, 2.0 km², 9.0% change. Zoom into one polygon. Show popup with construction category.

**[WORDS]**
Ladakh — strategic infrastructure monitoring. We compare May to July 2024 along the Leh–Manali corridor. Two polygons. 2.0 square kilometres. 9% change. Small in area — but this is a high-altitude desert where any surface change is significant. The model flags these as construction — elevated red band, suppressed NIR — the spectral signature of road widening and earthwork. This is the kind of change that matters for national security. And now India has an indigenous tool to detect it automatically, from open satellite data, with no foreign dependency.

---

## Segment 7 — AI Panel (3:15–3:30)

**[SCREEN]** Zoom into the AI Analysis panel on the right side of the dashboard. Show the natural-language summary text animating in. Show the model badge: "ChangeFormerV6 — Siamese Transformer Architecture | 41M params | 94.95% accuracy".

**[WORDS]**
Every analysis generates an automated intelligence brief — written by the system, not a human analyst. ChangeFormerV6, our Siamese Transformer model, uses dual hierarchical encoders to compare before and after imagery at four spatial scales simultaneously — capturing changes that a simple CNN would miss. The result: a structured brief that a field officer can act on immediately, without needing a remote-sensing PhD to interpret the output.

---

## Segment 8 — Closing Pitch (3:30–4:00)

**[SCREEN]** Fade to dark background. Three stats appear one by one:
- *"39 polygons | 297.71 km² | Navi Mumbai"*
- *"3 polygons | 12.2 km² | Assam/Bihar flood"*
- *"2 polygons | 2.0 km² | Ladakh corridor"*

Then full-screen text: *"Open source. Offline-first. Sovereign."*
Then: *"BharatDrishti — Built for Bharat, Powered by Open Science."*

**[WORDS]**
Three Indian regions. Three different challenges — urban growth, flood response, strategic infrastructure. One sovereign platform. Open-source, offline-first, deployable on ISRO servers or any Indian cloud. No subscription. No foreign API. No dependency. Plug in an ISRO Bhuvan feed and this runs on national satellite data in production tomorrow. BharatDrishti is not just a prototype — it is India's foundation for indigenous geospatial intelligence. This is Atmanirbhar Bharat, applied to the sky.

---

*Total estimated duration: ~3 minutes 45 seconds*
*Presenter pace: ~130 words/minute*
