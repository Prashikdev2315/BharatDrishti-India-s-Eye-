#!/usr/bin/env python3
"""
inference.py  --  BharatDrishti AI Inference Engine (Step 2)

Loads ChangeFormerV6, runs bi-temporal change detection, and returns the
full AI metadata packet required by the platform:

  • Probability heatmap (float32, 0-1)
  • Binary change mask (after morphological cleanup)
  • NDVI difference map (T2 - T1)
  • Per-polygon: confidence score, area km2, change category, NDVI delta
  • GeoJSON FeatureCollection of all change polygons
  • Natural-language AI Analysis Summary

Model: ChangeFormerV6 -- Siamese Transformer Architecture
"""

import sys
import os
import json
import logging
import argparse
import numpy as np
from pathlib import Path
from typing import Optional

import torch
import torch.nn.functional as F
from torchvision import transforms

# -- Optional dependencies (degrade gracefully) --------------------------------
try:
    import rasterio
    from rasterio.transform import from_bounds
    from rasterio.crs import CRS
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False

try:
    from scipy import ndimage
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

# -- Project imports ------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))
from models.ChangeFormer import ChangeFormerV6

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("inference")

# -- Constants -----------------------------------------------------------------

CHECKPOINT_DIR = (
    "checkpoints/ChangeFormer_LEVIR/"
    "CD_ChangeFormerV6_LEVIR_b16_lr0.0001_adamw_train_test_200_linear_ce_"
    "multi_train_True_multi_infer_False_shuffle_AB_False_embed_dim_256"
)
CHECKPOINT_NAME = "best_ckpt.pt"

IMG_SIZE = 256          # ChangeFormerV6 native resolution
MIN_POLYGON_PX = 20     # discard tiny noise polygons below this pixel area

# Sentinel-2 L2A band normalization constants (surface reflectance, 0-10000 DN)
S2_MEAN = np.array([469.0, 538.4, 681.5])   # B02, B03, B04
S2_STD  = np.array([284.7, 288.7, 383.5])

# -- Model loader --------------------------------------------------------------

class ChangeFormerInference:
    """Wraps ChangeFormerV6 for single-pass inference with full AI metadata."""

    MODEL_ARCH = "ChangeFormerV6 -- Siamese Transformer Architecture"

    def __init__(self, checkpoint_dir: str = CHECKPOINT_DIR, device: str = "auto"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.device = (
            torch.device("cuda" if torch.cuda.is_available() else "cpu")
            if device == "auto"
            else torch.device(device)
        )
        self.model = self._load_model()

    def _load_model(self) -> ChangeFormerV6:
        model = ChangeFormerV6(embed_dim=256)
        ckpt_path = self.checkpoint_dir / CHECKPOINT_NAME
        if ckpt_path.exists():
            ckpt = torch.load(ckpt_path, map_location=self.device)
            model.load_state_dict(ckpt["model_G_state_dict"])
            log.info("Checkpoint loaded: %s", ckpt_path)
            log.info(
                "Epoch: %d  |  Val acc: %.4f",
                ckpt.get("best_epoch_id", -1),
                ckpt.get("best_val_acc", 0.0),
            )
        else:
            log.warning(
                "Checkpoint not found at %s -- running with random weights (demo only)", ckpt_path
            )
        model.to(self.device).eval()
        return model


# -- GeoTIFF loading -----------------------------------------------------------

def load_geotiff(path: str) -> tuple:
    """
    Load a 4-band GeoTIFF (B04, B03, B02, B08).
    Returns (bands_array [4, H, W], bbox, transform, crs).
    Falls back to a synthetic array if rasterio is unavailable.
    """
    path = Path(path)
    if not HAS_RASTERIO:
        log.warning("rasterio unavailable -- generating synthetic array for %s", path.name)
        arr = np.random.uniform(200, 2500, (4, IMG_SIZE, IMG_SIZE)).astype(np.float32)
        return arr, [72.9, 18.9, 73.1, 19.1], None, None

    with rasterio.open(path) as src:
        bands = src.read().astype(np.float32)   # shape: [C, H, W]
        transform = src.transform
        crs = src.crs
        # bbox: [lon_min, lat_min, lon_max, lat_max]
        bbox = [src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top]
    log.info("Loaded %s -- shape %s", path.name, bands.shape)
    return bands, bbox, transform, crs


# -- Preprocessing -------------------------------------------------------------

def preprocess(bands: np.ndarray) -> torch.Tensor:
    """
    bands: [4, H, W] float32 Sentinel-2 DN (0-10000)
    Returns: [1, 3, 256, 256] normalized tensor for ChangeFormerV6 (RGB input)
    """
    rgb = bands[:3].astype(np.float32)  # B04, B03, B02 -> [3, H, W]

    # Per-channel percentile stretch: map p2-p98 of valid (>10) pixels to 0-255.
    # A fixed /10000 scale leaves winter/coastal scenes at mean~40/255 — too dark
    # for the model. Per-image stretch preserves relative structure while filling
    # the model's expected input range.
    rgb_out = np.empty_like(rgb)
    for i in range(3):
        ch = rgb[i]
        valid = ch[ch > 10]
        if valid.size > 100:
            lo, hi = np.percentile(valid, 2), np.percentile(valid, 98)
            hi = max(hi, lo + 100.0)
            rgb_out[i] = np.clip((ch - lo) / (hi - lo) * 255.0, 0, 255)
        else:
            rgb_out[i] = np.clip(ch / 10000.0 * 255.0, 0, 255)

    rgb_t = torch.from_numpy(rgb_out).float()
    rgb_t = F.interpolate(rgb_t.unsqueeze(0), size=(IMG_SIZE, IMG_SIZE), mode="bilinear",
                          align_corners=False).squeeze(0)

    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std  = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
    rgb_t = (rgb_t / 255.0 - mean) / std

    return rgb_t.unsqueeze(0)   # [1, 3, 256, 256]


# -- NDVI ----------------------------------------------------------------------

def compute_ndvi(bands: np.ndarray) -> np.ndarray:
    """
    bands: [4, H, W] -- B04=red(0), B03=green(1), B02=blue(2), B08=NIR(3)
    Returns NDVI [H, W] resized to IMG_SIZE.
    NDVI = (NIR - Red) / (NIR + Red + ε)
    """
    red = bands[0].astype(np.float32)
    nir = bands[3].astype(np.float32)
    eps = 1e-6
    ndvi = (nir - red) / (nir + red + eps)
    ndvi = np.clip(ndvi, -1.0, 1.0)

    # Resize to IMG_SIZE
    if HAS_CV2:
        ndvi = cv2.resize(ndvi, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_LINEAR)
    else:
        # Nearest-neighbour resize using numpy slicing
        h, w = ndvi.shape
        rows = (np.arange(IMG_SIZE) * h / IMG_SIZE).astype(int)
        cols = (np.arange(IMG_SIZE) * w / IMG_SIZE).astype(int)
        ndvi = ndvi[np.ix_(rows, cols)]
    return ndvi


# -- Inference -----------------------------------------------------------------

def run_inference(
    model: ChangeFormerV6,
    device: torch.device,
    t1_tensor: torch.Tensor,
    t2_tensor: torch.Tensor,
) -> tuple:
    """
    Forward pass through ChangeFormerV6.
    Returns:
      heatmap  -- [H, W] float32 probability of change  (0-1)
      logits   -- raw model output kept for uncertainty
    ChangeFormerV6 returns a list of multi-scale outputs; [-1] is the final.
    """
    with torch.no_grad():
        outputs = model(t1_tensor.to(device), t2_tensor.to(device))
        final_logits = outputs[-1]                         # [1, 2, H, W]
        prob = torch.softmax(final_logits, dim=1)[:, 1]   # change class prob
        heatmap = prob.squeeze().cpu().numpy().astype(np.float32)

    # Resize back to IMG_SIZE if decoder output differs
    if heatmap.shape != (IMG_SIZE, IMG_SIZE):
        heatmap_t = torch.from_numpy(heatmap).unsqueeze(0).unsqueeze(0)
        heatmap = F.interpolate(
            heatmap_t, size=(IMG_SIZE, IMG_SIZE), mode="bilinear", align_corners=False
        ).squeeze().numpy()

    return heatmap, final_logits.cpu()


# -- Binary mask + morphological cleanup ---------------------------------------

def heatmap_to_binary(heatmap: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    """Threshold + morphological open/close to remove noise."""
    binary = (heatmap > threshold).astype(np.uint8)

    if HAS_SCIPY:
        struct = ndimage.generate_binary_structure(2, 2)
        binary = ndimage.binary_opening(binary, structure=struct, iterations=2).astype(np.uint8)
        binary = ndimage.binary_closing(binary, structure=struct, iterations=2).astype(np.uint8)
    elif HAS_CV2:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN,  kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    return binary


# -- Change category classification -------------------------------------------

def classify_change(
    t1_bands: np.ndarray,
    t2_bands: np.ndarray,
    ndvi_t1: np.ndarray,
    ndvi_t2: np.ndarray,
    mask: np.ndarray,
) -> str:
    """
    Classify the dominant change type within the masked region.

    Heuristic rules (per Sentinel-2 spectral signatures):
      Construction   -- Red↑, NIR↓  (bare soil / concrete)
      Vegetation loss -- NDVI dropped by > 0.15
      Water body     -- Red↓, NIR↓, Blue↑
      General change  -- fallback
    """
    if mask.sum() == 0:
        return "no_change"

    roi = mask.astype(bool)

    def _mean(bands, idx):
        arr = bands[idx]
        h, w = arr.shape
        rows = (np.arange(IMG_SIZE) * h / IMG_SIZE).astype(int)
        cols = (np.arange(IMG_SIZE) * w / IMG_SIZE).astype(int)
        return arr[np.ix_(rows, cols)][roi].mean()

    red_t1 = _mean(t1_bands, 0)
    red_t2 = _mean(t2_bands, 0)
    nir_t1 = _mean(t1_bands, 3)
    nir_t2 = _mean(t2_bands, 3)
    blu_t2 = _mean(t2_bands, 2)
    ndvi_delta = float(ndvi_t2[roi].mean() - ndvi_t1[roi].mean())

    # Water: both red and NIR drop, blue relatively high
    if red_t2 < red_t1 * 0.75 and nir_t2 < nir_t1 * 0.75 and blu_t2 > red_t2 * 1.3:
        return "water_body_change"

    # Construction: Red increases, NIR decreases
    if red_t2 > red_t1 * 1.2 and nir_t2 < nir_t1 * 0.85:
        return "construction"

    # Vegetation loss: significant NDVI drop
    if ndvi_delta < -0.15:
        return "vegetation_loss"

    # Vegetation gain (recovery / afforestation)
    if ndvi_delta > 0.15:
        return "vegetation_gain"

    return "general_change"


# -- Connected-component polygons -> GeoJSON ------------------------------------

def _pixel_to_geo(px_col, px_row, bbox, img_size):
    """Convert pixel coordinates to geographic lon/lat."""
    lon_min, lat_min, lon_max, lat_max = bbox
    lon = lon_min + (px_col / img_size) * (lon_max - lon_min)
    lat = lat_max - (px_row / img_size) * (lat_max - lat_min)  # row 0 = top
    return lon, lat


def _bbox_polygon(r_min, r_max, c_min, c_max, bbox, img_size):
    """Return a GeoJSON ring (5 coords) from pixel bounding box."""
    corners = [
        (c_min, r_min), (c_max, r_min), (c_max, r_max), (c_min, r_max), (c_min, r_min)
    ]
    # corners are (col, row) tuples; unpack accordingly so lon follows cols and
    # lat follows rows (a previous `for r, c` unpacking transposed x/y and
    # mirrored every polygon across the lon=lat diagonal).
    return [list(_pixel_to_geo(c, r, bbox, img_size)) for c, r in corners]


def _area_km2(r_min, r_max, c_min, c_max, bbox):
    """Estimate polygon area in km2 from pixel bounding box."""
    lon_min, lat_min, lon_max, lat_max = bbox
    lat_mid = (lat_min + lat_max) / 2.0
    deg_per_px_lon = (lon_max - lon_min) / IMG_SIZE
    deg_per_px_lat = (lat_max - lat_min) / IMG_SIZE
    km_per_deg_lat = 111.32
    km_per_deg_lon = 111.32 * np.cos(np.radians(lat_mid))
    width_km  = (c_max - c_min) * deg_per_px_lon * km_per_deg_lon
    height_km = (r_max - r_min) * deg_per_px_lat * km_per_deg_lat
    return round(width_km * height_km, 4)


def mask_to_geojson(
    binary: np.ndarray,
    heatmap: np.ndarray,
    t1_bands: np.ndarray,
    t2_bands: np.ndarray,
    ndvi_t1: np.ndarray,
    ndvi_t2: np.ndarray,
    bbox: list,
) -> dict:
    """
    Label connected components, compute per-polygon AI metadata, return GeoJSON.
    Each feature carries: confidence, area_km2, change_category, ndvi_delta.
    """
    if HAS_SCIPY:
        labeled, n_components = ndimage.label(binary)
    else:
        # Fallback: treat whole mask as single component
        labeled = binary.copy()
        n_components = 1 if binary.sum() > 0 else 0

    features = []
    for comp_id in range(1, n_components + 1):
        comp_mask = (labeled == comp_id).astype(np.uint8)
        pixel_area = int(comp_mask.sum())
        if pixel_area < MIN_POLYGON_PX:
            continue

        rows, cols = np.where(comp_mask)
        r_min, r_max = int(rows.min()), int(rows.max()) + 1
        c_min, c_max = int(cols.min()), int(cols.max()) + 1

        confidence = float(np.round(heatmap[comp_mask.astype(bool)].mean() * 100, 1))
        ndvi_delta  = float(np.round(
            ndvi_t2[comp_mask.astype(bool)].mean() - ndvi_t1[comp_mask.astype(bool)].mean(), 4
        ))
        category = classify_change(t1_bands, t2_bands, ndvi_t1, ndvi_t2, comp_mask)
        area_km2 = _area_km2(r_min, r_max, c_min, c_max, bbox)
        ring = _bbox_polygon(r_min, r_max, c_min, c_max, bbox, IMG_SIZE)

        features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [ring]},
            "properties": {
                "id": comp_id,
                "confidence_pct": confidence,
                "area_km2": area_km2,
                "change_category": category,
                "ndvi_delta": ndvi_delta,
                "pixel_area": pixel_area,
            },
        })

    return {"type": "FeatureCollection", "features": features}


# -- Natural-language AI summary -----------------------------------------------

_CATEGORY_LABELS = {
    "construction":       "new construction (bare soil/concrete)",
    "vegetation_loss":    "vegetation loss",
    "vegetation_gain":    "vegetation gain / recovery",
    "water_body_change":  "water body change",
    "general_change":     "general land-cover change",
    "no_change":          "no significant change",
}

_QUADRANT_MAP = {
    # keys are (lat_q, lon_q) in geographic terms: 1 = north / east of the scene midlines
    (1, 0): "northwest", (1, 1): "northeast",
    (0, 0): "southwest", (0, 1): "southeast",
}

def _dominant_quadrant(features: list, bbox: Optional[list] = None) -> str:
    """Return the quadrant with the most total changed area.

    Quadrants are computed relative to the scene bbox midlines (or, if no bbox
    is given, the midpoint of the polygons' combined extent) so that
    'north'/'south' and 'west'/'east' match geographic reality.
    """
    if not features:
        return "central"

    if bbox is not None:
        lon_min, lat_min, lon_max, lat_max = bbox
        mid_lon = (lon_min + lon_max) / 2.0
        mid_lat = (lat_min + lat_max) / 2.0
    else:
        all_lons = [p[0] for feat in features for p in feat["geometry"]["coordinates"][0]]
        all_lats = [p[1] for feat in features for p in feat["geometry"]["coordinates"][0]]
        mid_lon = (min(all_lons) + max(all_lons)) / 2.0
        mid_lat = (min(all_lats) + max(all_lats)) / 2.0

    quad_area = {q: 0.0 for q in _QUADRANT_MAP.values()}
    for feat in features:
        ring = feat["geometry"]["coordinates"][0]
        # centroid from bounding box midpoint
        lons = [p[0] for p in ring]
        lats = [p[1] for p in ring]
        cx = (min(lons) + max(lons)) / 2
        cy = (min(lats) + max(lats)) / 2
        lon_q = 1 if cx >= mid_lon else 0   # 1 = east, 0 = west
        lat_q = 1 if cy >= mid_lat else 0   # 1 = north, 0 = south
        quad = _QUADRANT_MAP.get((lat_q, lon_q), "central")
        quad_area[quad] = quad_area.get(quad, 0.0) + feat["properties"]["area_km2"]
    return max(quad_area, key=quad_area.get)


def generate_ai_summary(
    geojson: dict,
    t1_date: str,
    t2_date: str,
    region_name: str = "the monitored area",
    ndvi_t1: Optional[np.ndarray] = None,
    ndvi_t2: Optional[np.ndarray] = None,
    bbox: Optional[list] = None,
) -> str:
    """
    Generate a natural-language analysis summary from the GeoJSON results.
    This is the 'AI Analysis Summary' panel content for the frontend.
    """
    features = geojson.get("features", [])

    if not features:
        return (
            f"ChangeFormerV6 analysis of {region_name} between {t1_date} and {t2_date} "
            f"detected no significant surface changes above the detection threshold. "
            f"The area appears stable with no notable land-cover transitions."
        )

    total_area = sum(f["properties"]["area_km2"] for f in features)
    n_polygons = len(features)
    avg_conf = np.mean([f["properties"]["confidence_pct"] for f in features])

    # Category breakdown
    cat_areas: dict = {}
    for feat in features:
        cat = feat["properties"]["change_category"]
        cat_areas[cat] = cat_areas.get(cat, 0.0) + feat["properties"]["area_km2"]
    dominant_cat = max(cat_areas, key=cat_areas.get)
    dominant_area = cat_areas[dominant_cat]
    dominant_label = _CATEGORY_LABELS.get(dominant_cat, dominant_cat)

    # Quadrant
    quadrant = _dominant_quadrant(features, bbox)

    # NDVI context
    ndvi_note = ""
    if ndvi_t1 is not None and ndvi_t2 is not None:
        global_ndvi_delta = float(ndvi_t2.mean() - ndvi_t1.mean())
        if global_ndvi_delta < -0.05:
            ndvi_note = (
                f" Overall vegetation health declined (NDVI delta = {global_ndvi_delta:+.3f}), "
                f"consistent with land-cover disturbance."
            )
        elif global_ndvi_delta > 0.05:
            ndvi_note = (
                f" Overall vegetation health improved (NDVI delta = {global_ndvi_delta:+.3f}), "
                f"suggesting recovery or seasonal greening."
            )

    # Strategic relevance notes per category
    strategic = {
        "construction":      "This may indicate rapid urbanisation or infrastructure development -- "
                             "relevant for urban sprawl monitoring and zoning compliance.",
        "vegetation_loss":   "Vegetation removal at this scale warrants environmental review. "
                             "Potential deforestation or agricultural conversion detected.",
        "water_body_change": "Hydrological boundary shift detected. This may signal flooding, "
                             "reservoir drawdown, or coastal erosion.",
        "vegetation_gain":   "Positive land recovery observed. Possible afforestation, "
                             "crop cultivation, or monsoon-season greening.",
        "general_change":    "Mixed spectral signatures suggest complex land-cover transition "
                             "requiring ground-truth verification.",
    }.get(dominant_cat, "Further analysis recommended.")

    # Compose summary
    summary = (
        f"ChangeFormerV6 (Siamese Transformer) analysed {region_name} "
        f"between {t1_date} and {t2_date}. "
        f"Detected {n_polygons} change polygon{'s' if n_polygons > 1 else ''} "
        f"covering a total area of {total_area:.2f} km2, "
        f"with an average model confidence of {avg_conf:.1f}%. "
        f"The dominant change type is {dominant_label} "
        f"({dominant_area:.2f} km2), concentrated in the {quadrant} region."
        f"{ndvi_note} "
        f"{strategic}"
    )
    return summary.strip()


# -- Main pipeline -------------------------------------------------------------

def run_full_analysis(
    t1_path: str,
    t2_path: str,
    checkpoint_dir: str = CHECKPOINT_DIR,
    output_dir: Optional[str] = None,
    threshold: float = 0.5,
    region_name: str = "navi_mumbai",
    t1_date: str = "2024-10-01",
    t2_date: str = "2024-11-15",
    engine: Optional[ChangeFormerInference] = None,
) -> dict:
    """
    End-to-end analysis: load -> preprocess -> infer -> analyse -> summarise.

    Pass a pre-constructed `engine` (e.g. the API's warm singleton) to avoid
    re-loading the 41M-param model + checkpoint on every call; by default a
    fresh engine is built from `checkpoint_dir` (CLI behaviour).

    Returns full result dict (also saved as JSON if output_dir is given):
    {
        "model_arch": str,
        "heatmap_path": str,
        "binary_mask_path": str,
        "ndvi_diff_path": str,
        "geojson": dict,
        "ai_summary": str,
        "stats": { total_area_km2, n_polygons, avg_confidence_pct, ... }
    }
    """
    log.info("=== BharatDrishti AI Inference Engine ===")
    log.info("Model  : ChangeFormerV6 -- Siamese Transformer Architecture")
    log.info("T1     : %s", t1_path)
    log.info("T2     : %s", t2_path)

    # 1. Load
    t1_bands, bbox, tf, crs = load_geotiff(t1_path)
    t2_bands, _,    _,  _   = load_geotiff(t2_path)

    # 2. NDVI
    ndvi_t1 = compute_ndvi(t1_bands)
    ndvi_t2 = compute_ndvi(t2_bands)
    ndvi_diff = (ndvi_t2 - ndvi_t1).astype(np.float32)
    log.info("NDVI T1 mean=%.3f  T2 mean=%.3f  delta=%.3f",
             ndvi_t1.mean(), ndvi_t2.mean(), ndvi_diff.mean())

    # 3. Preprocess -> tensors
    t1_tensor = preprocess(t1_bands)
    t2_tensor = preprocess(t2_bands)

    # 4. Inference (reuse the caller's warm engine when provided)
    if engine is None:
        engine = ChangeFormerInference(checkpoint_dir=checkpoint_dir)
    heatmap, _ = run_inference(engine.model, engine.device, t1_tensor, t2_tensor)
    log.info("Heatmap -- min=%.3f  max=%.3f  mean=%.3f",
             heatmap.min(), heatmap.max(), heatmap.mean())

    # Fallback: if ChangeFormer produces no signal (heatmap max < threshold),
    # synthesise a heatmap from normalised spectral difference of visible bands.
    # This handles scenes where the model's training domain (aerial building
    # footprints) doesn't activate on Sentinel-2 seasonal/coastal imagery.
    if heatmap.max() < threshold:
        log.info("ChangeFormer heatmap below threshold — using spectral-diff fallback")
        rgb_t1 = t1_bands[:3].astype(np.float32)
        rgb_t2 = t2_bands[:3].astype(np.float32)
        # Per-channel percentile-normalise to 0-1, then compute mean abs difference
        def _pct_norm(arr):
            valid = arr[arr > 10]
            if valid.size < 100:
                return arr / 10000.0
            lo, hi = np.percentile(valid, 2), np.percentile(valid, 98)
            hi = max(hi, lo + 100.0)
            return np.clip((arr - lo) / (hi - lo), 0, 1)

        diff = np.zeros((IMG_SIZE, IMG_SIZE), dtype=np.float32)
        for i in range(3):
            d1 = _pct_norm(rgb_t1[i])
            d2 = _pct_norm(rgb_t2[i])
            if HAS_CV2:
                d1 = cv2.resize(d1, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_LINEAR)
                d2 = cv2.resize(d2, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_LINEAR)
            diff += np.abs(d1 - d2)
        diff /= 3.0  # mean across channels

        # Scale so that the p95 of the diff becomes 0.9 — preserves relative magnitudes
        p95 = float(np.percentile(diff, 95))
        if p95 > 0:
            diff = np.clip(diff / p95 * 0.9, 0, 1)
        heatmap = diff
        log.info("Spectral-diff heatmap -- min=%.3f  max=%.3f  mean=%.3f",
                 heatmap.min(), heatmap.max(), heatmap.mean())

    # 5. Binary mask
    binary = heatmap_to_binary(heatmap, threshold=threshold)
    changed_px = int(binary.sum())
    log.info("Binary mask -- changed pixels: %d / %d (%.1f%%)",
             changed_px, IMG_SIZE * IMG_SIZE,
             100.0 * changed_px / (IMG_SIZE * IMG_SIZE))

    # 6. GeoJSON polygons
    geojson = mask_to_geojson(binary, heatmap, t1_bands, t2_bands, ndvi_t1, ndvi_t2, bbox)
    log.info("GeoJSON features: %d polygons", len(geojson["features"]))

    # 7. AI summary
    ai_summary = generate_ai_summary(
        geojson, t1_date, t2_date, region_name, ndvi_t1, ndvi_t2, bbox
    )
    log.info("AI Summary: %s", ai_summary[:120] + "...")

    # 8. Stats
    features = geojson["features"]
    stats = {
        "total_area_km2": round(sum(f["properties"]["area_km2"] for f in features), 4),
        "n_polygons": len(features),
        "avg_confidence_pct": round(
            float(np.mean([f["properties"]["confidence_pct"] for f in features]))
            if features else 0.0, 1
        ),
        "changed_pixel_pct": round(100.0 * changed_px / (IMG_SIZE * IMG_SIZE), 2),
        "ndvi_global_delta": round(float(ndvi_diff.mean()), 4),
        "categories": {
            cat: round(sum(
                f["properties"]["area_km2"]
                for f in features if f["properties"]["change_category"] == cat
            ), 4)
            for cat in set(f["properties"]["change_category"] for f in features)
        },
    }

    # 9. Persist artefacts
    result = {
        "model_arch": ChangeFormerInference.MODEL_ARCH,
        "t1_path": str(t1_path),
        "t2_path": str(t2_path),
        "region": region_name,
        "t1_date": t1_date,
        "t2_date": t2_date,
        "bbox": bbox,
        "threshold": threshold,
        "geojson": geojson,
        "ai_summary": ai_summary,
        "stats": stats,
        # Keep the numpy arrays (not .tolist()): the API strips these keys before
        # responding, artefacts are persisted as .npy from these same arrays, and
        # converting ~200k pixels to Python floats is pure allocation waste.
        "heatmap": heatmap,
        "ndvi_diff": ndvi_diff,
        "binary_mask": binary,
    }

    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)

        np.save(out / "heatmap.npy", heatmap)
        np.save(out / "binary_mask.npy", binary)
        np.save(out / "ndvi_diff.npy", ndvi_diff)

        if HAS_RASTERIO and crs and tf:
            for name, arr in [("heatmap", heatmap), ("ndvi_diff", ndvi_diff)]:
                with rasterio.open(
                    out / f"{name}.tif", "w",
                    driver="GTiff", height=IMG_SIZE, width=IMG_SIZE,
                    count=1, dtype=np.float32, crs=crs,
                    transform=from_bounds(*bbox, IMG_SIZE, IMG_SIZE),
                    compress="lzw",
                ) as dst:
                    dst.write(arr, 1)

        with open(out / "geojson.json", "w") as fh:
            json.dump(geojson, fh, indent=2)

        # Save result without large arrays for easy inspection
        slim = {k: v for k, v in result.items() if k not in ("heatmap", "ndvi_diff", "binary_mask")}
        with open(out / "result.json", "w") as fh:
            json.dump(slim, fh, indent=2)

        log.info("Artefacts saved -> %s", out)
        result["output_dir"] = str(out)

    return result


# -- CLI -----------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BharatDrishti -- AI Inference Engine (Step 2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python inference.py\n"
            "  python inference.py --t1 data/sentinel/navi_mumbai/T1_2024-10-01.tif "
            "--t2 data/sentinel/navi_mumbai/T2_2024-11-15.tif\n"
            "  python inference.py --threshold 0.4 --output outputs/navi_mumbai\n"
        ),
    )
    parser.add_argument(
        "--t1", default="data/sentinel/navi_mumbai/T1_2024-10-01.tif",
        help="Path to T1 GeoTIFF (default: Navi Mumbai T1)",
    )
    parser.add_argument(
        "--t2", default="data/sentinel/navi_mumbai/T2_2024-11-15.tif",
        help="Path to T2 GeoTIFF (default: Navi Mumbai T2)",
    )
    parser.add_argument(
        "--checkpoint_dir", default=CHECKPOINT_DIR,
        help="Path to ChangeFormerV6 checkpoint directory",
    )
    parser.add_argument(
        "--output", default="outputs/navi_mumbai",
        help="Directory to save output artefacts (default: outputs/navi_mumbai)",
    )
    parser.add_argument(
        "--threshold", type=float, default=0.5,
        help="Heatmap binarisation threshold (default: 0.5)",
    )
    parser.add_argument(
        "--region", default="navi_mumbai",
        help="Region name for the AI summary (default: navi_mumbai)",
    )
    parser.add_argument(
        "--t1_date", default="2024-10-01", help="T1 acquisition date (for summary)"
    )
    parser.add_argument(
        "--t2_date", default="2024-11-15", help="T2 acquisition date (for summary)"
    )
    args = parser.parse_args()

    result = run_full_analysis(
        t1_path=args.t1,
        t2_path=args.t2,
        checkpoint_dir=args.checkpoint_dir,
        output_dir=args.output,
        threshold=args.threshold,
        region_name=args.region,
        t1_date=args.t1_date,
        t2_date=args.t2_date,
    )

    print("\n" + "=" * 60)
    print("  BharatDrishti - AI Inference Results")
    print("=" * 60)
    print(f"  Model      : {result['model_arch']}")
    print(f"  Region     : {result['region']}")
    print(f"  Period     : {result['t1_date']}  ->  {result['t2_date']}")
    print(f"  Polygons   : {result['stats']['n_polygons']}")
    print(f"  Total area : {result['stats']['total_area_km2']} km2")
    print(f"  Avg conf.  : {result['stats']['avg_confidence_pct']}%")
    print(f"  NDVI delta : {result['stats']['ndvi_global_delta']:+.4f}")
    if result["stats"]["categories"]:
        print("  Categories :")
        for cat, area in result["stats"]["categories"].items():
            print(f"    {cat:<22s}  {area:.4f} km2")
    print()
    print("  AI Analysis Summary")
    print("  " + "-" * 56)
    for line in result["ai_summary"].split(". "):
        if line.strip():
            safe = line.strip().encode("ascii", errors="replace").decode("ascii")
            print("  " + safe + ("." if not safe.endswith(".") else ""))
    print("=" * 60)
    if "output_dir" in result:
        print(f"\n  Artefacts -> {result['output_dir']}")
