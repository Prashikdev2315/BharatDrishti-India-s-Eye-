#!/usr/bin/env python3
"""
sentinel_fetch.py  —  BharatDrishti Data Pipeline (Step 1)

Downloads Sentinel-2 bi-temporal image pairs from Copernicus Data Space
Ecosystem (CDSE).  Falls back to pre-cached synthetic GeoTIFFs for fully
offline / hackathon demo operation.

Bands fetched : B04 (Red), B03 (Green), B02 (Blue), B08 (NIR)
Output        : data/sentinel/<region>/T1_<date>.tif  +  T2_<date>.tif
"""

import os
import json
import logging
import numpy as np
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict

try:
    import rasterio
    from rasterio.transform import from_bounds
    from rasterio.crs import CRS
    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False
    print("[WARN] rasterio not installed — install it with: pip install rasterio")

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("sentinel_fetch")

# ── API endpoints ─────────────────────────────────────────────────────────────

CDSE_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu"
    "/auth/realms/CDSE/protocol/openid-connect/token"
)
CDSE_SEARCH_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
CDSE_DOWNLOAD_URL = "https://download.dataspace.copernicus.eu/odata/v1/Products"

# ── Demo regions ──────────────────────────────────────────────────────────────

REGIONS: Dict[str, dict] = {
    "navi_mumbai": {
        "bbox": [72.8, 18.9, 73.0, 19.1],
        "t1": "2023-01-01",
        "t2": "2024-01-01",
        "description": "Navi Mumbai coast — urban construction detection",
        "scene_type": "coastal_urban",
    },
    "assam_bihar": {
        "bbox": [91.5, 25.5, 91.8, 25.8],
        "t1": "2024-05-01",
        "t2": "2024-09-01",
        "description": "Assam/Bihar — flood zone change detection",
        "scene_type": "floodplain",
    },
    "ladakh_highway": {
        "bbox": [77.5, 34.0, 77.8, 34.3],
        "t1": "2024-05-01",
        "t2": "2024-07-01",
        "description": "Ladakh highway — strategic infrastructure monitoring",
        "scene_type": "mountain_arid",
    },
}

BANDS = ["B04", "B03", "B02", "B08"]
IMG_SIZE = 512
DATA_DIR = Path("data/sentinel")


# ── Authentication ────────────────────────────────────────────────────────────

def get_token(username: str, password: str) -> Optional[str]:
    """Obtain a short-lived CDSE access token via Resource Owner Password flow."""
    try:
        resp = requests.post(
            CDSE_TOKEN_URL,
            data={
                "grant_type": "password",
                "username": username,
                "password": password,
                "client_id": "cdse-public",
            },
            timeout=15,
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]
        log.info("CDSE authentication successful")
        return token
    except Exception as exc:
        log.warning("Token fetch failed (%s) — switching to offline mode", exc)
        return None


# ── Catalogue search ──────────────────────────────────────────────────────────

def search_scenes(
    bbox: list,
    date_str: str,
    token: Optional[str] = None,
    max_cloud: int = 30,
) -> list:
    """
    Search CDSE OData catalogue for Sentinel-2 L2A scenes near the given date.
    Window is ±3 days; results sorted by cloud cover ascending.
    """
    lon_min, lat_min, lon_max, lat_max = bbox
    date = datetime.strptime(date_str, "%Y-%m-%d")
    t_start = (date - timedelta(days=3)).strftime("%Y-%m-%dT00:00:00.000Z")
    t_end = (date + timedelta(days=3)).strftime("%Y-%m-%dT23:59:59.999Z")

    footprint = (
        f"POLYGON(({lon_min} {lat_min},{lon_max} {lat_min},"
        f"{lon_max} {lat_max},{lon_min} {lat_max},{lon_min} {lat_min}))"
    )

    params = {
        "$filter": (
            "Collection/Name eq 'SENTINEL-2' and "
            "Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' "
            "and att/OData.CSC.StringAttribute/Value eq 'S2MSI2A') and "
            f"ContentDate/Start ge {t_start} and ContentDate/Start le {t_end} and "
            f"OData.CSC.Intersects(area=geography'SRID=4326;{footprint}') and "
            "Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' "
            f"and att/OData.CSC.DoubleAttribute/Value le {max_cloud})"
        ),
        "$orderby": (
            "Attributes/OData.CSC.DoubleAttribute/any("
            "att:att/Name eq 'cloudCover') asc"
        ),
        "$top": "3",
    }

    headers = {"Authorization": f"Bearer {token}"} if token else {}

    try:
        resp = requests.get(CDSE_SEARCH_URL, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
        products = resp.json().get("value", [])
        log.info("Catalogue: %d scene(s) found for %s ± 3 days", len(products), date_str)
        return products
    except Exception as exc:
        log.warning("Catalogue search failed: %s", exc)
        return []


# ── Product download ──────────────────────────────────────────────────────────

def download_product(product_id: str, token: str, dest_path: Path) -> bool:
    """Stream-download a full Sentinel-2 product zip by its CDSE UUID."""
    url = f"{CDSE_DOWNLOAD_URL}({product_id})/$value"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with requests.get(url, headers=headers, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length", 0))
            written = 0
            with open(dest_path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    fh.write(chunk)
                    written += len(chunk)
            log.info("Downloaded %s  (%.1f MB)", dest_path.name, written / 1e6)
        return True
    except Exception as exc:
        log.warning("Download failed: %s", exc)
        return False


# ── Synthetic fallback ────────────────────────────────────────────────────────

def _blob_mask(size: int, n_blobs: int, seed: int) -> np.ndarray:
    """Return a [0,1] density map built from Gaussian blobs."""
    rng = np.random.default_rng(seed)
    mask = np.zeros((size, size), dtype=np.float32)
    y_idx, x_idx = np.ogrid[:size, :size]
    for _ in range(n_blobs):
        cx, cy = rng.integers(0, size, 2)
        r = rng.integers(8, size // 8)
        mask += np.exp(-((x_idx - cx) ** 2 + (y_idx - cy) ** 2) / (2.0 * r ** 2))
    peak = mask.max()
    return (mask / peak).clip(0, 1) if peak > 0 else mask


def generate_synthetic_tiff(
    bbox: list,
    out_path: Path,
    scene_type: str = "coastal_urban",
    seed: int = 42,
    add_change: bool = False,
) -> Path:
    """
    Create a 4-band (B04, B03, B02, B08) GeoTIFF with plausible Sentinel-2
    surface-reflectance DN values (0–10000 scale).

    `add_change=True` injects a new construction patch (T2 scenario):
    elevated red/SWIR, depressed NIR — characteristic of bare soil / concrete.
    """
    if not HAS_RASTERIO:
        raise RuntimeError("rasterio is required — pip install rasterio")

    size = IMG_SIZE
    rng = np.random.default_rng(seed)
    noise = lambda s=50: rng.normal(0, s, (size, size)).astype(np.float32)

    urban = _blob_mask(size, n_blobs=25, seed=seed)
    veg = np.clip(1.0 - urban + noise(0.04), 0, 1)

    # Water body — small coastal strip (scene-type dependent)
    water = np.zeros((size, size), dtype=np.float32)
    if scene_type == "coastal_urban":
        water[:, : size // 6] = _blob_mask(size, n_blobs=5, seed=seed + 1)[:, : size // 6]
    elif scene_type == "floodplain":
        water[size // 3 : 2 * size // 3, :] = (
            _blob_mask(size, n_blobs=8, seed=seed + 2)[size // 3 : 2 * size // 3, :]
        )

    # Band synthesis — Sentinel-2 L2A typical range 0–10000
    b04 = (urban * 1300 + veg * 450 + water * 120 + noise(55)).clip(0, 10000)
    b03 = (urban * 1050 + veg * 620 + water * 250 + noise(55)).clip(0, 10000)
    b02 = (urban * 920 + veg * 530 + water * 750 + noise(55)).clip(0, 10000)
    b08 = (urban * 820 + veg * 4800 + water * 200 + noise(80)).clip(0, 10000)

    if add_change:
        # New construction patch: high Red, low NIR — bare soil / concrete signature
        y_c, x_c = size // 3, size // 3
        r_patch = size // 12
        y_idx, x_idx = np.ogrid[:size, :size]
        patch = (x_idx - x_c) ** 2 + (y_idx - y_c) ** 2 < r_patch ** 2
        b04[patch] = rng.uniform(2200, 2800, patch.sum())
        b03[patch] = rng.uniform(1700, 2100, patch.sum())
        b02[patch] = rng.uniform(1500, 1900, patch.sum())
        b08[patch] = rng.uniform(800, 1100, patch.sum())

    lon_min, lat_min, lon_max, lat_max = bbox
    transform = from_bounds(lon_min, lat_min, lon_max, lat_max, size, size)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        out_path, "w",
        driver="GTiff",
        height=size, width=size,
        count=4,
        dtype=np.float32,
        crs=CRS.from_epsg(4326),
        transform=transform,
        compress="lzw",
    ) as dst:
        for idx, band_arr in enumerate([b04, b03, b02, b08], start=1):
            dst.write(band_arr.astype(np.float32), idx)
        dst.update_tags(
            BANDS="B04,B03,B02,B08",
            SCENE_TYPE=scene_type,
            SYNTHETIC="TRUE",
            CHANGE_INJECTED=str(add_change),
            GENERATED_UTC=datetime.utcnow().isoformat(),
        )

    kb = out_path.stat().st_size / 1024
    log.info("Synthetic GeoTIFF saved  →  %s  (%.0f KB)", out_path, kb)
    return out_path


# ── Main pipeline entry point ─────────────────────────────────────────────────

def fetch_pair(
    region_name: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    force_offline: bool = False,
) -> dict:
    """
    Fetch or generate T1/T2 GeoTIFF pair for a demo region.

    Resolution order:
      1. Existing on-disk cache (instant return)
      2. Live CDSE download (if credentials supplied and online)
      3. Synthetic offline generation (always succeeds)

    Returns {"t1": Path, "t2": Path, "region": str, "bbox": list, "source": str}
    """
    if region_name not in REGIONS:
        raise ValueError(f"Unknown region '{region_name}'. Choose from: {list(REGIONS)}")

    region = REGIONS[region_name]
    bbox = region["bbox"]
    scene_type = region["scene_type"]
    cache_dir = DATA_DIR / region_name
    t1_path = cache_dir / f"T1_{region['t1']}.tif"
    t2_path = cache_dir / f"T2_{region['t2']}.tif"

    # 1. Cache hit
    if t1_path.exists() and t2_path.exists():
        log.info("[CACHE HIT] %s — skipping download", region_name)
        source = "CACHED"
    else:
        source = "SYNTHETIC_OFFLINE"

        # 2. Live CDSE attempt
        if not force_offline and username and password:
            token = get_token(username, password)
            if token:
                for date_str, out_path in [(region["t1"], t1_path), (region["t2"], t2_path)]:
                    if out_path.exists():
                        continue
                    scenes = search_scenes(bbox, date_str, token)
                    if scenes:
                        pid = scenes[0]["Id"]
                        name = scenes[0].get("Name", pid)
                        log.info("Best scene for %s: %s", date_str, name)
                        zip_dest = cache_dir / f"{pid}.zip"
                        if download_product(pid, token, zip_dest):
                            # Full SAFE-format extraction is out of demo scope.
                            # The zip is saved; band extraction would use sentinelsat
                            # or manual SAFE/JP2 parsing in production.
                            log.info(
                                "Product zip saved. Generating registered synthetic "
                                "as stand-in for demo (production: extract JP2 bands)."
                            )
                source = "CDSE_API+SYNTHETIC_STANDIN"

        # 3. Synthetic generation
        if not t1_path.exists():
            log.info("Generating T1 (%s)  →  %s", region["t1"], t1_path)
            generate_synthetic_tiff(bbox, t1_path, scene_type=scene_type, seed=101, add_change=False)

        if not t2_path.exists():
            log.info("Generating T2 (%s)  →  %s", region["t2"], t2_path)
            generate_synthetic_tiff(bbox, t2_path, scene_type=scene_type, seed=102, add_change=True)

    # Save / refresh metadata
    meta = {
        "region": region_name,
        "description": region["description"],
        "bbox": bbox,
        "t1_date": region["t1"],
        "t2_date": region["t2"],
        "t1_path": str(t1_path),
        "t2_path": str(t2_path),
        "bands": BANDS,
        "img_size": IMG_SIZE,
        "source": source,
        "fetched_at": datetime.utcnow().isoformat(),
    }
    meta_path = cache_dir / "meta.json"
    cache_dir.mkdir(parents=True, exist_ok=True)
    with open(meta_path, "w") as fh:
        json.dump(meta, fh, indent=2)

    log.info("Metadata  →  %s", meta_path)
    return {**meta, "t1": t1_path, "t2": t2_path}


def prefetch_all(username=None, password=None, force_offline=False) -> dict:
    """Pre-cache all three demo regions."""
    results = {}
    for region_name in REGIONS:
        log.info("═══  %s  ═══", region_name)
        results[region_name] = fetch_pair(region_name, username, password, force_offline)
    return results


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="BharatDrishti — Sentinel-2 data pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python sentinel_fetch.py --offline\n"
            "  python sentinel_fetch.py --region assam_bihar --offline --inspect\n"
            "  python sentinel_fetch.py --all --offline\n"
            "  python sentinel_fetch.py --username <email> --password <pw>\n"
        ),
    )
    parser.add_argument(
        "--region", default="navi_mumbai", choices=list(REGIONS),
        help="Region to fetch (default: navi_mumbai)",
    )
    parser.add_argument("--all", action="store_true", help="Pre-cache all three demo regions")
    parser.add_argument("--username", default=os.getenv("CDSE_USER"), help="CDSE username/email")
    parser.add_argument("--password", default=os.getenv("CDSE_PASS"), help="CDSE password")
    parser.add_argument("--offline", action="store_true", help="Skip API — use synthetic data only")
    parser.add_argument("--inspect", action="store_true", help="Print per-band stats after fetch")
    cli = parser.parse_args()

    if cli.all:
        results = prefetch_all(cli.username, cli.password, cli.offline)
        target = results["navi_mumbai"]   # inspect first region by default
    else:
        target = fetch_pair(cli.region, cli.username, cli.password, cli.offline)

    print("\n-- Pair ready --")
    print(f"  Region : {target['region']}")
    print(f"  T1     : {target['t1']}")
    print(f"  T2     : {target['t2']}")
    print(f"  Source : {target['source']}")
    print(f"  BBox   : {target['bbox']}")

    if cli.inspect and HAS_RASTERIO:
        print()
        for label, path in [("T1", target["t1"]), ("T2", target["t2"])]:
            with rasterio.open(path) as src:
                print(f"── {label}: {path} ──")
                print(f"   CRS    : {src.crs}")
                print(f"   Size   : {src.width} × {src.height}")
                print(f"   Bands  : {src.count}  [{src.meta['dtype']}]")
                band_names = ["B04(Red)", "B03(Grn)", "B02(Blu)", "B08(NIR)"]
                for b in range(1, src.count + 1):
                    data = src.read(b)
                    print(
                        f"   {band_names[b-1]:12s}: "
                        f"min={data.min():6.0f}  max={data.max():6.0f}  "
                        f"mean={data.mean():6.0f}"
                    )
            print()
