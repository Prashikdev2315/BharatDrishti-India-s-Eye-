#!/usr/bin/env python3
"""Re-fetch Navi Mumbai with corrected bbox [72.8, 18.9, 73.0, 19.1] inside T43QBA."""

import os, requests, logging
from pathlib import Path
from sentinel_real import get_token, download_and_extract, DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("fix_mumbai2")

CDSE_SEARCH_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

# Shifted bbox: fully inside T43QBA (the 265.8 MB tile)
BBOX = [72.8, 18.9, 73.0, 19.1]

# Both from T43QBA — same tile, consistent geography
TARGETS = [
    {
        "which": "T1", "date": "2024-10-01",
        "name": "S2B_MSIL2A_20241005T052649_N0511_R105_T43QBA_20241005T081613.SAFE",
    },
    {
        "which": "T2", "date": "2024-11-15",
        "name": "S2A_MSIL2A_20241112T054051_N0511_R005_T43QBA_20241112T080853.SAFE",
    },
]

def fetch_by_name(product_name, token):
    filt = f"Name eq '{product_name}'"
    resp = requests.get(
        CDSE_SEARCH_URL,
        params={"$filter": filt, "$top": "1"},
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    resp.raise_for_status()
    products = resp.json().get("value", [])
    if not products:
        raise RuntimeError(f"Product not found: {product_name}")
    return products[0]

def main():
    username = os.getenv("CDSE_USER")
    password = os.getenv("CDSE_PASS")
    if not username or not password:
        raise SystemExit("Set CDSE_USER and CDSE_PASS env vars")

    token = get_token(username, password)
    cache_dir = DATA_DIR / "navi_mumbai"
    cache_dir.mkdir(parents=True, exist_ok=True)

    for target in TARGETS:
        out_path = cache_dir / f"{target['which']}_{target['date']}.tif"
        log.info("Fetching %s -> %s (bbox=%s)", target["name"][:60], out_path, BBOX)
        product = fetch_by_name(target["name"], token)
        ok = download_and_extract(product, token, BBOX, out_path)
        if ok:
            log.info("✓  %s done", target["which"])
        else:
            log.error("✗  %s failed", target["which"])

if __name__ == "__main__":
    main()
