#!/usr/bin/env python3
"""
Fetch real Sentinel-2 data for all 3 BharatDrishti regions
"""
import os
import sys
import logging
from pathlib import Path
from sentinel_real import (
    get_token, search_best_scene, download_and_extract,
    REGIONS, DATA_DIR
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("fetch_all")

def main():
    username = os.getenv("CDSE_USER")
    password = os.getenv("CDSE_PASS")

    if not username or not password:
        log.error("Environment variables CDSE_USER and CDSE_PASS must be set")
        sys.exit(1)

    log.info("=== BharatDrishti Real Data Fetch ===")
    log.info("Authenticating with Copernicus CDSE...")

    try:
        token = get_token(username, password)
    except Exception as e:
        log.error("Authentication failed: %s", e)
        sys.exit(1)

    for region_name, config in REGIONS.items():
        log.info("")
        log.info("=" * 60)
        log.info("REGION: %s", region_name)
        log.info("=" * 60)

        bbox = config["bbox"]
        cache_dir = DATA_DIR / region_name
        cache_dir.mkdir(parents=True, exist_ok=True)

        for which, date_str in [("T1", config["t1"]), ("T2", config["t2"])]:
            out_path = cache_dir / f"{which}_{date_str}.tif"

            log.info("")
            log.info("--- Fetching %s: %s ---", which, date_str)

            try:
                product = search_best_scene(bbox, date_str, token, max_cloud=50, window_days=7)

                if not product:
                    log.warning("No scenes found for %s %s -- keeping synthetic", region_name, date_str)
                    continue

                success = download_and_extract(product, token, bbox, out_path)

                if success:
                    log.info("✓ %s %s downloaded successfully", region_name, which)
                else:
                    log.warning("✗ %s %s download failed -- keeping synthetic", region_name, which)

            except Exception as e:
                log.error("Error fetching %s %s: %s", region_name, which, e)
                log.warning("Keeping synthetic data for this timestamp")
                continue

    log.info("")
    log.info("=" * 60)
    log.info("REAL DATA FETCH COMPLETE")
    log.info("=" * 60)

if __name__ == "__main__":
    main()
