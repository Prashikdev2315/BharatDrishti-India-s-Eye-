#!/usr/bin/env python3
"""Fetch real Sentinel-2 data for hackathon demo with updated dates/bboxes."""
import os, logging
from pathlib import Path
from sentinel_real import get_token, search_best_scene, download_and_extract, DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("fetch_demo")

CDSE_USER = os.getenv("CDSE_USER")
CDSE_PASS = os.getenv("CDSE_PASS")

if not CDSE_USER or not CDSE_PASS:
    raise ValueError("Set CDSE_USER and CDSE_PASS environment variables")

# Updated targets for better demo
TARGETS = [
    ("navi_mumbai", [72.8, 18.9, 73.0, 19.1], "2023-01-01", "2024-01-01"),
    ("assam_bihar", [91.5, 25.5, 91.8, 25.8], "2024-05-01", "2024-09-01"),
    ("ladakh_highway", [77.5, 34.0, 77.8, 34.3], "2024-05-01", "2024-07-01"),
]

def main():
    token = get_token(CDSE_USER, CDSE_PASS)

    for region_id, bbox, t1_date, t2_date in TARGETS:
        log.info("=" * 60)
        log.info("Fetching %s: %s -> %s", region_id, t1_date, t2_date)
        log.info("Bbox: %s", bbox)

        cache_dir = DATA_DIR / region_id
        cache_dir.mkdir(parents=True, exist_ok=True)

        for which, date_str in [("T1", t1_date), ("T2", t2_date)]:
            out_path = cache_dir / f"{which}_{date_str}.tif"
            if out_path.exists():
                log.info("%s already exists, skipping", out_path.name)
                continue

            log.info("Searching %s/%s (%s)", region_id, which, date_str)
            product = search_best_scene(bbox, date_str, token, max_cloud=80, window_days=10)
            if not product:
                log.error("No scene found for %s/%s near %s", region_id, which, date_str)
                continue

            log.info("Downloading %s", product["Name"][:65])
            success = download_and_extract(product, token, bbox, out_path)
            if success:
                log.info("✅ %s complete", out_path.name)
            else:
                log.error("❌ %s failed", out_path.name)

        log.info("✅ %s region complete", region_id)

    log.info("🎯 All regions fetched successfully!")

if __name__ == "__main__":
    main()
