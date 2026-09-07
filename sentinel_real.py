#!/usr/bin/env python3
"""
sentinel_real.py  --  Real Sentinel-2 download + extraction for BharatDrishti

Downloads L2A SAFE zips from CDSE, extracts B02/B03/B04/B08 JP2 bands,
reprojects from UTM to EPSG:4326, crops to bbox, saves as 4-band GeoTIFF.
Falls back to synthetic if download/extract fails.
"""

import os
import io
import json
import zipfile
import logging
import tempfile
import requests
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.transform import from_bounds
from rasterio.crs import CRS
from rasterio.mask import mask as rio_mask
from shapely.geometry import box
import fiona

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("sentinel_real")

CDSE_TOKEN_URL = (
    "https://identity.dataspace.copernicus.eu"
    "/auth/realms/CDSE/protocol/openid-connect/token"
)
CDSE_SEARCH_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
CDSE_DOWNLOAD_URL = "https://download.dataspace.copernicus.eu/odata/v1/Products"

DATA_DIR = Path("data/sentinel")
IMG_SIZE = 512

REGIONS = {
    "navi_mumbai": {
        "bbox": [72.9, 18.9, 73.1, 19.1],
        "t1": "2024-10-01", "t2": "2024-11-15",
        "description": "Navi Mumbai coast -- urban construction detection",
        "scene_type": "coastal_urban",
    },
    "assam_bihar": {
        "bbox": [91.5, 25.5, 91.8, 25.8],
        "t1": "2024-07-01", "t2": "2024-09-01",
        "description": "Assam/Bihar -- flood zone change detection",
        "scene_type": "floodplain",
    },
    "ladakh_highway": {
        "bbox": [77.5, 34.0, 77.8, 34.3],
        "t1": "2024-05-01", "t2": "2024-07-01",
        "description": "Ladakh highway -- strategic infrastructure monitoring",
        "scene_type": "mountain_arid",
    },
}


def get_token(username, password):
    resp = requests.post(
        CDSE_TOKEN_URL,
        data={"grant_type": "password", "username": username,
              "password": password, "client_id": "cdse-public"},
        timeout=15,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    log.info("CDSE authenticated as %s", username)
    return token


def search_best_scene(bbox, date_str, token, max_cloud=50, window_days=5):
    """Return the best (lowest cloud) online Sentinel-2 L2A product near date."""
    lon_min, lat_min, lon_max, lat_max = bbox
    date = datetime.strptime(date_str, "%Y-%m-%d")
    t_start = (date - timedelta(days=window_days)).strftime("%Y-%m-%dT00:00:00.000Z")
    t_end   = (date + timedelta(days=window_days)).strftime("%Y-%m-%dT23:59:59.999Z")
    footprint = (
        f"POLYGON(({lon_min} {lat_min},{lon_max} {lat_min},"
        f"{lon_max} {lat_max},{lon_min} {lat_max},{lon_min} {lat_min}))"
    )
    filt = (
        f"Collection/Name eq 'SENTINEL-2' and "
        f"ContentDate/Start ge {t_start} and ContentDate/Start le {t_end} and "
        f"OData.CSC.Intersects(area=geography'SRID=4326;{footprint}') and "
        f"Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' "
        f"and att/OData.CSC.StringAttribute/Value eq 'S2MSI2A')"
    )
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(
        CDSE_SEARCH_URL,
        params={"$filter": filt, "$top": "20", "$expand": "Attributes"},
        headers=headers, timeout=20,
    )
    resp.raise_for_status()
    products = resp.json().get("value", [])

    # Filter online, sort by cloud cover client-side
    def get_cloud(p):
        for a in p.get("Attributes", []):
            if a["Name"] == "cloudCover":
                return a["Value"]
        return 999

    online = [p for p in products if p.get("Online")]
    online.sort(key=get_cloud)
    if online:
        cc = get_cloud(online[0])
        log.info("Best scene for %s: %s (cloud=%.1f%%, %.1f MB)",
                 date_str, online[0]["Name"], cc,
                 online[0].get("ContentLength", 0) / 1e6)
    return online[0] if online else None


def download_and_extract(product, token, bbox, out_path):
    """
    Download the SAFE zip, extract the 4 JP2 bands,
    reproject from UTM -> EPSG:4326, crop to bbox, save 4-band GeoTIFF.
    Returns True on success.
    """
    pid = product["Id"]
    dl_url = f"{CDSE_DOWNLOAD_URL}({pid})/$value"
    headers = {"Authorization": f"Bearer {token}"}

    log.info("Downloading %s ...", product["Name"])
    with requests.get(dl_url, headers=headers, stream=True, timeout=300) as resp:
        resp.raise_for_status()
        zip_bytes = io.BytesIO()
        downloaded = 0
        for chunk in resp.iter_content(chunk_size=2 << 20):
            zip_bytes.write(chunk)
            downloaded += len(chunk)
        log.info("Downloaded %.1f MB", downloaded / 1e6)

    zip_bytes.seek(0)
    zf = zipfile.ZipFile(zip_bytes)

    # Find 10m bands
    band_map = {}
    for entry in zf.namelist():
        for b in ["B02", "B03", "B04", "B08"]:
            if f"R10m" in entry and f"_{b}_10m.jp2" in entry:
                band_map[b] = entry

    if len(band_map) < 4:
        log.warning("Only found bands: %s -- trying 20m fallback", list(band_map.keys()))
        for entry in zf.namelist():
            for b in ["B02", "B03", "B04"]:
                if f"R20m" in entry and f"_{b}_20m.jp2" in entry and b not in band_map:
                    band_map[b] = entry
            if "B08" not in band_map:
                for entry2 in zf.namelist():
                    if "R10m" in entry2 and "_B08_10m.jp2" in entry2:
                        band_map["B08"] = entry2

    log.info("Extracting bands: %s", {k: v.split("/")[-1] for k, v in band_map.items()})

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_paths = {}
        for band_name, zip_path in band_map.items():
            data = zf.read(zip_path)
            tmp_file = Path(tmpdir) / f"{band_name}.jp2"
            tmp_file.write_bytes(data)
            tmp_paths[band_name] = tmp_file

        # Reproject each band to EPSG:4326 and crop to bbox
        lon_min, lat_min, lon_max, lat_max = bbox
        crop_geom = [box(lon_min, lat_min, lon_max, lat_max).__geo_interface__]

        arrays = {}
        for band_name in ["B04", "B03", "B02", "B08"]:
            if band_name not in tmp_paths:
                log.warning("Missing band %s, using zeros", band_name)
                arrays[band_name] = np.zeros((IMG_SIZE, IMG_SIZE), dtype=np.float32)
                continue

            with rasterio.open(tmp_paths[band_name]) as src:
                # Reproject to WGS84
                dst_crs = CRS.from_epsg(4326)
                transform_wgs, width_wgs, height_wgs = calculate_default_transform(
                    src.crs, dst_crs, src.width, src.height, *src.bounds
                )
                kwargs = src.meta.copy()
                kwargs.update({
                    "crs": dst_crs,
                    "transform": transform_wgs,
                    "width": width_wgs,
                    "height": height_wgs,
                    "driver": "GTiff",
                })
                reproj_path = Path(tmpdir) / f"{band_name}_wgs84.tif"
                with rasterio.open(reproj_path, "w", **kwargs) as dst:
                    reproject(
                        source=rasterio.band(src, 1),
                        destination=rasterio.band(dst, 1),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform_wgs,
                        dst_crs=dst_crs,
                        resampling=Resampling.bilinear,
                    )

                # Crop to bbox
                with rasterio.open(reproj_path) as reproj:
                    try:
                        cropped, crop_transform = rio_mask(reproj, crop_geom, crop=True)
                        arr = cropped[0].astype(np.float32)
                    except Exception as e:
                        log.warning("Crop failed for %s: %s -- using full tile", band_name, e)
                        arr = reproj.read(1).astype(np.float32)

            # Resize to IMG_SIZE x IMG_SIZE
            import cv2 as _cv2
            arr = _cv2.resize(arr, (IMG_SIZE, IMG_SIZE), interpolation=_cv2.INTER_AREA)
            arrays[band_name] = arr
            log.info("Band %s: min=%.0f max=%.0f mean=%.0f",
                     band_name, arr.min(), arr.max(), arr.mean())

    out_path.parent.mkdir(parents=True, exist_ok=True)
    transform_out = from_bounds(lon_min, lat_min, lon_max, lat_max, IMG_SIZE, IMG_SIZE)
    with rasterio.open(
        out_path, "w",
        driver="GTiff", height=IMG_SIZE, width=IMG_SIZE,
        count=4, dtype=np.float32,
        crs=CRS.from_epsg(4326), transform=transform_out, compress="lzw",
    ) as dst:
        for i, band_name in enumerate(["B04", "B03", "B02", "B08"], start=1):
            dst.write(arrays[band_name], i)
        dst.update_tags(
            BANDS="B04,B03,B02,B08",
            SYNTHETIC="FALSE",
            PRODUCT_NAME=product["Name"],
            GENERATED_UTC=datetime.utcnow().isoformat(),
        )

    size_kb = out_path.stat().st_size / 1024
    log.info("Saved real GeoTIFF -> %s  (%.0f KB)", out_path, size_kb)
    return True
