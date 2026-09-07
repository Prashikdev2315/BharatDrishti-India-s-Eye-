# BharatDrishti — Demo Video Script (Simple Version)
# Duration: ~3:45 | Screen: http://127.0.0.1:5173 only
# Format: [TIME] | [SCREEN ACTION] | [WORDS TO SAY]

---

[0:00–0:30] | Show the BharatDrishti homepage — full dashboard visible, three region cards in sidebar, map centred on India | Every day, Sentinel-2 satellites pass over every corner of India — from the Ladakh border to the Navi Mumbai coast to the Brahmaputra floodplains. They capture everything: new construction, flood events, deforestation, road expansion. 290 terabytes of raw intelligence. Almost none of it gets analysed in time to matter. Today we show you how India watches itself.

---

[0:30–1:00] | Keep dashboard visible, point camera at screen — do not click anything yet | The tools that exist today — Google Earth Engine, Planet Labs — are American-controlled, subscription-gated platforms. If India's border monitoring or disaster response depends on a US company's API staying online, that is not sovereignty. That is dependency. There is no Indian-built, AI-powered, offline-capable system for monitoring land-cover change across Indian territory — until now.

---

[1:00–1:30] | Scroll slowly down the sidebar to show the three region cards: Navi Mumbai, Assam/Bihar, Ladakh | BharatDrishti — India's Eye — ingests free Copernicus Sentinel-2 satellite data and runs it through ChangeFormerV6, a Siamese Transformer AI model with 41 million parameters, achieving 94.95% accuracy on change detection benchmarks. It delivers change heatmaps, GeoJSON polygons, NDVI vegetation maps, and an automated AI analysis brief. It runs 100% offline on Indian infrastructure. No foreign API. No subscription.

---

[1:30–1:50] | Click the Navi Mumbai region card. Wait for the loading spinner to finish. The map populates with red polygons over the coastal area | We select Navi Mumbai — a full year of change, January 2023 to January 2024. The system processes bi-temporal Sentinel-2 imagery and returns 39 detected change polygons, covering 297.71 square kilometres — 46.9% of the monitored area.

---

[1:50–2:15] | Drag the before/after compare slider slowly from right to left, then back to the middle. Then click the largest red polygon on the map — the popup appears showing confidence, area, category, and NDVI delta | Watch the before-after slider: January 2023 — tidal mudflat and open ground. January 2024 — entire construction zones have emerged. We click a polygon: 12.4 km², confidence 51%, category construction, NDVI delta minus 0.18. That NDVI drop — near-infrared falling, red rising — is the spectral signature of bare soil replacing vegetation. Classic construction pattern.

---

[2:15–2:45] | Click the Assam/Bihar region card. Wait for results. The map recentres to northeastern India showing three large blue polygons. Scroll down the stats panel to show: 3 polygons, 12.2 km², water_body_change category | Assam and Bihar — India's flood belt. May to September 2024, straddling the monsoon peak. Three polygons, 12.2 km², category: water body change. The NDVI map confirms it — areas where standing water replaced vegetation during the flood event. Each polygon here represents thousands of affected families. This is the rapid environmental monitoring NDMA needs in real time.

---

[2:45–3:15] | Click the Ladakh region card. Wait for results. Map recentres to high-altitude terrain. Two compact polygons visible. Click one polygon to open its popup showing: 2 polygons, 2.0 km², 9.0% change, construction category | Ladakh — strategic infrastructure monitoring. May to July 2024, Leh–Manali corridor. Two polygons. 2.0 square kilometres. 9% change. Small in area — but in a high-altitude desert, any surface change is significant. Elevated red band, suppressed NIR — the spectral signature of road widening and earthwork. India now has an indigenous tool to detect this automatically, from open satellite data, with zero foreign dependency.

---

[3:15–3:30] | Scroll the right panel to the AI Analysis section. Let the full natural-language summary text be visible on screen. Point to the model badge showing ChangeFormerV6 | Every analysis generates an automated intelligence brief — written by the system, not a human analyst. ChangeFormerV6 uses dual hierarchical encoders to compare before and after imagery at four spatial scales simultaneously, capturing changes a simple CNN would miss. A structured brief a field officer can act on immediately, without needing a remote-sensing PhD.

---

[3:30–4:00] | Scroll back up to show the full dashboard — map, AI panel, and region cards all visible at once | Three Indian regions. Three different challenges — urban growth, flood response, strategic infrastructure. One sovereign platform. Open-source, offline-first, deployable on ISRO servers. No subscription. No foreign API. Plug in an ISRO Bhuvan feed and this runs on national satellite data in production tomorrow. BharatDrishti is India's foundation for indigenous geospatial intelligence. This is Atmanirbhar Bharat, applied to the sky.

---

*Total estimated duration: ~3 minutes 45 seconds*
*All screen actions on http://127.0.0.1:5173 only*
