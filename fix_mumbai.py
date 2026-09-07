#!/usr/bin/env python3
"""Re-fetch Navi Mumbai using T43QBB for both T1 and T2 (consistent tile)."""

import os, requests, logging
from sentinel_real import get_token, download_and_extract, DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("fix_mumbai")

CDSE_SEARCH_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

BBOX = [72.9, 18.9, 73.1, 19.1]

# Scenes from T43QBB that appear in both date windows (identified by prior search)
TARGETS = [
    {
        "which": "T1", "date": "2024-10-01",
        "name": "S2B_MSIL2A_20241005T052649_N0511_R105_T43QBB_20241005T081613.SAFE",
    },
    {
        "which": "T2", "date": "2024-11-15",
        "name": "S2A_MSIL2A_20241112T054051_N0511_R005_T43QBB_20241112T080853.SAFE",
    },
]

def fetch_by_name(product_name, token):
    """Look up a product by exact name and return its record."""
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
        log.info("Fetching %s -> %s", target["name"][:60], out_path)
        product = fetch_by_name(target["name"], token)
        ok = download_and_extract(product, token, BBOX, out_path)
        if ok:
            log.info("✓  %s done", target["which"])
        else:
            log.error("✗  %s failed", target["which"])

if __name__ == "__main__":
    main()
