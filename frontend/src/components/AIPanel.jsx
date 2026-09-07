const CATEGORY_LABELS = {
  construction: "Construction",
  vegetation_loss: "Vegetation Loss",
  vegetation_gain: "Vegetation Gain",
  water_body_change: "Water Body Change",
  general_change: "General Change",
  no_change: "No Change",
};

export default function AIPanel({ analysis, showHeatmap, onToggleHeatmap }) {
  if (!analysis) {
    return (
      <aside className="ai-panel ai-panel--empty">
        <p>Select a region to run the ChangeFormer AI analysis.</p>
      </aside>
    );
  }

  const { stats, ai_summary, model_arch } = analysis;
  const categories = Object.entries(stats.categories || {});

  return (
    <aside className="ai-panel">
      <div className="ai-panel__model-badge">
        <span className="pulse-dot" />
        Powered by ChangeFormer — Siamese Transformer Architecture
      </div>

      <button
        className={`heatmap-toggle ${showHeatmap ? "heatmap-toggle--on" : ""}`}
        onClick={onToggleHeatmap}
      >
        {showHeatmap ? "🔥 Heatmap: ON" : "🔥 Heatmap: OFF"}
      </button>

      <div className="ai-panel__confidence">
        <span className="ai-panel__confidence-value">{stats.avg_confidence_pct}%</span>
        <span className="ai-panel__confidence-label">Model Confidence</span>
      </div>

      <div className="ai-panel__stat-grid">
        <div className="stat-tile">
          <span className="stat-tile__value">{stats.total_area_km2}</span>
          <span className="stat-tile__label">km² changed</span>
        </div>
        <div className="stat-tile">
          <span className="stat-tile__value">{stats.n_polygons}</span>
          <span className="stat-tile__label">zones detected</span>
        </div>
        <div className="stat-tile">
          <span
            className={`stat-tile__value ${stats.ndvi_global_delta < 0 ? "negative" : "positive"}`}
          >
            {stats.ndvi_global_delta > 0 ? "+" : ""}
            {stats.ndvi_global_delta}
          </span>
          <span className="stat-tile__label">NDVI Δ</span>
        </div>
        <div className="stat-tile">
          <span className="stat-tile__value">{stats.changed_pixel_pct}%</span>
          <span className="stat-tile__label">surface changed</span>
        </div>
      </div>

      {categories.length > 0 && (
        <div className="ai-panel__categories">
          <h3>Change Category Breakdown</h3>
          {categories.map(([cat, area]) => (
            <div className="category-row" key={cat}>
              <span className={`category-dot category-dot--${cat}`} />
              <span className="category-row__name">
                {CATEGORY_LABELS[cat] || cat}
              </span>
              <span className="category-row__value">{area.toFixed(2)} km²</span>
            </div>
          ))}
        </div>
      )}

      <div className="ai-panel__summary">
        <h3>AI Analysis Summary</h3>
        <p>{ai_summary}</p>
      </div>

      <div className="ai-panel__footer-note">Model: {model_arch}</div>
    </aside>
  );
}
