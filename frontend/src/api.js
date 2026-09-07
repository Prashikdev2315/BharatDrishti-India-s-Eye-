export const API_BASE = "http://127.0.0.1:8000";

async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Request failed: ${url} (${res.status})`);
  }
  return res.json();
}

export function fetchRegions() {
  return getJSON(`${API_BASE}/api/regions`);
}

export function fetchAnalysis(region, { refresh = false } = {}) {
  const q = refresh ? "?refresh=true" : "";
  return getJSON(`${API_BASE}/api/analyze/${region}${q}`);
}

export function fetchModelInfo() {
  return getJSON(`${API_BASE}/api/model-info`);
}

export function thumbnailUrl(region, which) {
  return `${API_BASE}/api/thumbnail/${region}/${which}.png`;
}

export function heatmapUrl(region) {
  return `${API_BASE}/api/heatmap/${region}.png`;
}

export function ndviDiffUrl(region) {
  return `${API_BASE}/api/ndvi-diff/${region}.png`;
}
