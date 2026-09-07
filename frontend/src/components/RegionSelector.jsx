const REGION_LABELS = {
  navi_mumbai: { label: "Navi Mumbai", hint: "Urban construction" },
  assam_bihar: { label: "Assam / Bihar", hint: "Flood zone change" },
  ladakh_highway: { label: "Ladakh Highway", hint: "Strategic infrastructure" },
};

export default function RegionSelector({ regions, selected, onSelect, disabled }) {
  return (
    <div className="region-selector">
      {regions.map((region) => {
        const meta = REGION_LABELS[region.id] || { label: region.id, hint: "" };
        const isActive = region.id === selected;
        return (
          <button
            key={region.id}
            className={`region-btn ${isActive ? "region-btn--active" : ""}`}
            onClick={() => onSelect(region.id)}
            disabled={disabled}
          >
            <span className="region-btn__label">{meta.label}</span>
            <span className="region-btn__hint">{meta.hint}</span>
          </button>
        );
      })}
    </div>
  );
}
