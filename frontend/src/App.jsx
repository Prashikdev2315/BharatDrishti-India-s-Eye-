import { useEffect, useRef, useState } from "react";
import Header from "./components/Header";
import Footer from "./components/Footer";
import RegionSelector from "./components/RegionSelector";
import CompareSlider from "./components/CompareSlider";
import MapView from "./components/MapView";
import AIPanel from "./components/AIPanel";
import LoadingOverlay from "./components/LoadingOverlay";
import { fetchRegions, fetchAnalysis } from "./api";
import "./App.css";

const LOADING_MESSAGES = [
  "Fetching satellite imagery...",
  "Running ChangeFormer AI analysis...",
  "Generating change report...",
];

export default function App() {
  const [regions, setRegions] = useState([]);
  const [selectedRegion, setSelectedRegion] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState(LOADING_MESSAGES[0]);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [error, setError] = useState(null);
  const messageTimer = useRef(null);

  useEffect(() => {
    fetchRegions()
      .then((data) => setRegions(data.regions))
      .catch(() => setError("Could not reach BharatDrishti backend at http://127.0.0.1:8000"));
  }, []);

  const runAnalysis = async (regionId) => {
    setSelectedRegion(regionId);
    setShowHeatmap(false);
    setLoading(true);
    setError(null);

    let step = 0;
    setLoadingMessage(LOADING_MESSAGES[0]);
    messageTimer.current = setInterval(() => {
      step = Math.min(step + 1, LOADING_MESSAGES.length - 1);
      setLoadingMessage(LOADING_MESSAGES[step]);
    }, 700);

    // Cached regions resolve in ~70ms — enforce a minimum display time so the
    // "Fetching -> Analysing -> Generating" sequence is actually visible to the demo audience.
    const MIN_DISPLAY_MS = 700 * LOADING_MESSAGES.length;
    const minDelay = new Promise((resolve) => setTimeout(resolve, MIN_DISPLAY_MS));

    try {
      const [data] = await Promise.all([fetchAnalysis(regionId), minDelay]);
      setAnalysis(data);
    } catch (err) {
      setError(`Analysis failed for ${regionId}: ${err.message}`);
      setAnalysis(null);
    } finally {
      clearInterval(messageTimer.current);
      setLoading(false);
    }
  };

  const activeRegionMeta = regions.find((r) => r.id === selectedRegion);

  return (
    <div className="app-shell">
      <Header />

      <RegionSelector
        regions={regions}
        selected={selectedRegion}
        onSelect={runAnalysis}
        disabled={loading}
      />

      {error && <div className="error-banner">{error}</div>}

      <main className="app-main">
        <section className="app-main__left">
          {analysis ? (
            <CompareSlider
              region={selectedRegion}
              t1Date={analysis.t1_date}
              t2Date={analysis.t2_date}
            />
          ) : (
            <div className="compare-card compare-card--placeholder">
              <p>Pick a demo region above to load before/after satellite imagery.</p>
            </div>
          )}

          <MapView
            bbox={activeRegionMeta?.bbox || analysis?.bbox}
            geojson={analysis?.geojson}
            region={selectedRegion}
            showHeatmap={showHeatmap}
          />
        </section>

        <AIPanel
          analysis={analysis}
          showHeatmap={showHeatmap}
          onToggleHeatmap={() => setShowHeatmap((v) => !v)}
        />
      </main>

      <Footer />

      {loading && <LoadingOverlay message={loadingMessage} />}
    </div>
  );
}
