#!/usr/bin/env python3
"""
api.py  --  BharatDrishti FastAPI Backend (Step 3)

Serves AI change-detection results for the React/Leaflet frontend.
Every response carries the full AI/Deep-Tech metadata: model architecture,
per-polygon confidence, NDVI delta, change category, and a natural-language
AI Analysis Summary.

Runs 100% offline: results are computed once by inference.py and cached to
outputs/<region>/result.json; the API serves that cache and regenerates it
on demand (--refresh) or if missing.
"""

import io
import json
import logging
from pathlib import Path
from typing import Callable, Optional

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("api")

from sentinel_fetch import REGIONS, fetch_pair
import inference as infer_mod

OUTPUT_ROOT = Path("outputs")
MODEL_ARCH = "ChangeFormerV6 -- Siamese Transformer Architecture"

app = FastAPI(
    title="BharatDrishti API",
    description="Indigenous satellite geospatial intelligence -- AI change detection backend",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # demo/hackathon scope -- tighten for production
    allow_methods=["*"],
    allow_headers=["*"],
)

_engine: Optional["infer_mod.ChangeFormerInference"] = None


def get_engine() -> "infer_mod.ChangeFormerInference":
    """Lazy-load the ChangeFormerV6 model once and reuse across requests."""
    global _engine
    if _engine is None:
        log.info("Loading ChangeFormerV6 model into memory...")
        _engine = infer_mod.ChangeFormerInference()
    return _engine


def _result_path(region: str) -> Path:
    return OUTPUT_ROOT / region / "result.json"


def get_or_compute_result(region: str, force: bool = False) -> dict:
    """Load cached AI analysis, or run the full pipeline if missing/forced."""
    if region not in REGIONS:
        raise HTTPException(status_code=404, detail=f"Unknown region '{region}'. Choices: {list(REGIONS)}")

    result_path = _result_path(region)
    if result_path.exists() and not force:
        with open(result_path) as fh:
            return json.load(fh)

    log.info("No cached result for '%s' -- running inference pipeline", region)
    pair = fetch_pair(region, force_offline=True)
    meta = REGIONS[region]

    engine = get_engine()  # warm singleton -- reused inside run_full_analysis below
    result = infer_mod.run_full_analysis(
        t1_path=str(pair["t1"]),
        t2_path=str(pair["t2"]),
        output_dir=str(OUTPUT_ROOT / region),
        region_name=region,
        t1_date=meta["t1"],
        t2_date=meta["t2"],
        engine=engine,
    )
    # Strip large arrays before returning/caching via API (raster endpoints read the .npy directly)
    slim = {k: v for k, v in result.items() if k not in ("heatmap", "ndvi_diff", "binary_mask")}
    return slim


def _load_raster(region: str, name: str) -> np.ndarray:
    path = OUTPUT_ROOT / region / f"{name}.npy"
    if not path.exists():
        get_or_compute_result(region)  # populate cache
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{name} not available for region '{region}'")
    return np.load(path)


# -- PNG response cache ---------------------------------------------------------
# Rendered PNGs are byte-identical between inference runs; caching them avoids
# re-decoding rasters + re-encoding images on every request. Entries are keyed
# by the source file's mtime, so a ?refresh=true re-run (which rewrites the
# .npy/GeoTIFF files) invalidates stale entries automatically.

_png_cache: dict = {}   # key: (kind, region) -> (source_mtime, png_bytes)


def _cached_png(key: tuple, source_path: Path, render: Callable[[], bytes]) -> bytes:
    """Return render()'s bytes, reusing the cached copy while source mtime is unchanged."""
    def _mtime():
        return source_path.stat().st_mtime if source_path.exists() else None

    entry = _png_cache.get(key)
    if entry is not None and entry[0] == _mtime():
        return entry[1]

    png = render()
    _png_cache[key] = (_mtime(), png)
    return png


def _raster_png_response(region: str, name: str, cmap: str, vmin: float, vmax: float) -> Response:
    """Shared renderer for the .npy-backed PNG endpoints (with caching)."""
    path = OUTPUT_ROOT / region / f"{name}.npy"

    def render() -> bytes:
        arr = _load_raster(region, name)
        if name == "binary_mask":
            arr = arr.astype(np.float32)
        return _array_to_png(arr, cmap=cmap, vmin=vmin, vmax=vmax)

    return Response(
        content=_cached_png((name, region), path, render),
        media_type="image/png",
    )


def _array_to_png(arr: np.ndarray, cmap: str, vmin: float = None, vmax: float = None) -> bytes:
    """Render a 2D float array to a colorized, transparent-background PNG."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.cm as cm
    import matplotlib.colors as mcolors
    from PIL import Image

    vmin = float(arr.min()) if vmin is None else vmin
    vmax = float(arr.max()) if vmax is None else vmax
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    try:  # matplotlib >= 3.6 registry (get_cmap is removed in 3.9)
        colormap = matplotlib.colormaps[cmap]
    except AttributeError:  # pragma: no cover -- older matplotlib fallback
        colormap = cm.get_cmap(cmap)
    rgba = (colormap(norm(arr)) * 255).astype(np.uint8)   # [H, W, 4]

    img = Image.fromarray(rgba, mode="RGBA")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    return {
        "name": "BharatDrishti API",
        "tagline": "India's Eye -- Sovereign Satellite Intelligence",
        "model": MODEL_ARCH,
        "regions": list(REGIONS.keys()),
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "model_loaded": _engine is not None}


@app.get("/api/model-info")
def model_info():
    """Static model metadata for the 'Powered by ChangeFormer' UI badge."""
    return {
        "name": "ChangeFormerV6",
        "architecture": MODEL_ARCH,
        "description": (
            "A Siamese-Transformer network for bi-temporal remote-sensing change "
            "detection. Dual hierarchical transformer encoders extract multi-scale "
            "features from before/after imagery; a lightweight MLP decoder fuses "
            "the differenced features into a pixel-wise change probability map."
        ),
        "training_dataset": "LEVIR-CD (building change detection, Sentinel/aerial imagery)",
        "params_m": 41.0,
        "val_accuracy": 0.9495,
    }


@app.get("/api/regions")
def list_regions():
    """List demo regions with bbox/date metadata for the map picker."""
    out = []
    for name, cfg in REGIONS.items():
        out.append({
            "id": name,
            "description": cfg["description"],
            "bbox": cfg["bbox"],
            "t1_date": cfg["t1"],
            "t2_date": cfg["t2"],
            "scene_type": cfg["scene_type"],
            "has_cached_result": _result_path(name).exists(),
        })
    return {"regions": out}


@app.get("/api/analyze/{region}")
def analyze(region: str, refresh: bool = Query(False, description="Force re-run inference")):
    """
    Full AI analysis payload for a region:
    model info, GeoJSON change polygons (confidence/category/NDVI per polygon),
    stats, and the natural-language AI Analysis Summary.
    """
    result = get_or_compute_result(region, force=refresh)
    return JSONResponse(content=result)


@app.get("/api/heatmap/{region}.png")
def heatmap_png(region: str):
    """Change-intensity heatmap (not binary) as a colorized PNG for map overlay."""
    return _raster_png_response(region, "heatmap", cmap="inferno", vmin=0.0, vmax=1.0)


@app.get("/api/ndvi-diff/{region}.png")
def ndvi_diff_png(region: str):
    """NDVI difference (vegetation health change) as a diverging colorized PNG."""
    return _raster_png_response(region, "ndvi_diff", cmap="RdYlGn", vmin=-0.5, vmax=0.5)


@app.get("/api/mask/{region}.png")
def binary_mask_png(region: str):
    """Binary change mask (post morphological cleanup) as a black/white PNG."""
    return _raster_png_response(region, "binary_mask", cmap="gray", vmin=0.0, vmax=1.0)


@app.get("/api/geojson/{region}")
def geojson(region: str):
    """Change polygons only, as a standalone GeoJSON FeatureCollection."""
    result = get_or_compute_result(region)
    return JSONResponse(content=result["geojson"])


@app.get("/api/summary/{region}")
def summary(region: str):
    """AI Analysis Summary text + key stats, for the summary panel."""
    result = get_or_compute_result(region)
    return {
        "ai_summary": result["ai_summary"],
        "stats": result["stats"],
        "model_arch": result["model_arch"],
    }


@app.get("/api/thumbnail/{region}/{which}.png")
def thumbnail(region: str, which: str):
    """
    RGB preview (B04/B03/B02 as R/G/B) of T1 or T2 for the before/after slider.
    which: 't1' | 't2'
    """
    if which not in ("t1", "t2"):
        raise HTTPException(status_code=400, detail="which must be 't1' or 't2'")
    if region not in REGIONS:
        raise HTTPException(status_code=404, detail=f"Unknown region '{region}'")

    pair = fetch_pair(region, force_offline=True)
    path = pair["t1"] if which == "t1" else pair["t2"]

    def render() -> bytes:
        bands, _, _, _ = infer_mod.load_geotiff(str(path))
        rgb = bands[:3].astype(np.float32)                       # B04,B03,B02
        rgb = np.clip(rgb / 3000.0, 0, 1) ** 0.8                 # simple stretch + gamma
        rgb = (rgb * 255).astype(np.uint8)
        rgb = np.transpose(rgb, (1, 2, 0))                       # [H, W, 3]

        from PIL import Image
        img = Image.fromarray(rgb, mode="RGB")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    png = _cached_png((f"thumbnail-{which}", region), Path(path), render)
    return Response(content=png, media_type="image/png")


@app.post("/api/analyze/{region}/refresh")
def refresh_analysis(region: str):
    """Force a fresh inference run for a region (bypasses cache)."""
    result = get_or_compute_result(region, force=True)
    return JSONResponse(content=result)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
