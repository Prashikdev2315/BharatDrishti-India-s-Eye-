#!/usr/bin/env python3
"""Re-fetch Navi Mumbai T1 using R005 orbit (same ground track as T2)."""

import os, requests, logging
from sentinel_real import get_token, download_and_extract, DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("fix_mumbai3")

CDSE_SEARCH_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
BBOX = [72.8, 18.9, 73.0, 19.1]

# Oct 8, R005, T43QBA — same orbit as T2 (Nov 12 R005)
T1_PRODUCT = "S2B_MSIL2A_20241008T053639_N0511_R005_T43QBA_20241008T081925.SAFE"

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
    out_path = cache_dir / "T1_2024-10-01.tif"

    log.info("Fetching T1 (R005 orbit): %s", T1_PRODUCT)
    product = fetch_by_name(T1_PRODUCT, token)
    ok = download_and_extract(product, token, BBOX, out_path)
    log.info("✓ T1 done" if ok else "✗ T1 failed")

if __name__ == "__main__":
    main()
