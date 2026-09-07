export default function Header() {
  return (
    <header className="app-header">
      <div className="app-header__brand">
        <span className="app-header__logo">🛰️</span>
        <div>
          <h1 className="app-header__title">BharatDrishti</h1>
          <p className="app-header__subtitle">India's Eye — Indigenous Geospatial Intelligence</p>
        </div>
      </div>
      <div className="app-header__right">
        <div className="demo-mode-badge" title="Runs fully offline on pre-cached satellite data">
          <span className="demo-mode-badge__dot" />
          Demo Mode — 100% Offline
        </div>
        <div className="app-header__badge">
          <span className="dot" />
          Powered by ChangeFormer — Siamese Transformer Architecture
        </div>
      </div>
    </header>
  );
}
