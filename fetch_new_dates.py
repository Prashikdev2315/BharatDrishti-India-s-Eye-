#!/usr/bin/env python3
"""
Fetch new data for Mumbai (2023->2024 one-year gap) and
Assam (pre-monsoon Apr 2024 -> post-monsoon Sep 2024).
"""
import os, requests, logging
from sentinel_real import get_token, download_and_extract, DATA_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s %(message)s")
log = logging.getLogger("fetch_new_dates")

CDSE_SEARCH_URL = "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"

TARGETS = [
    # Mumbai: T1=Jan 2 2023, T2=Jan 2 2024 — same R005 orbit, 1-year gap
    {
        "region": "navi_mumbai",
        "bbox": [72.8, 18.9, 73.0, 19.1],
        "which": "T1", "date": "2023-01-01",
        "name": "S2A_MSIL2A_20230102T054231_N0510_R005_T43QBA_20240810T160335.SAFE",
    },
    {
        "region": "navi_mumbai",
        "bbox": [72.8, 18.9, 73.0, 19.1],
        "which": "T2", "date": "2024-01-01",
        "name": "S2B_MSIL2A_20240102T054229_N0510_R005_T43QBA_20240102T072106.SAFE",
    },
    # Assam: T1=Apr 25 2024 (pre-monsoon, 5% cloud), T2=Sep 7 2024 (post-flood, 48% cloud)
    {
        "region": "assam_bihar",
        "bbox": [91.5, 25.5, 91.8, 25.8],
        "which": "T1", "date": "2024-05-01",
        "name": "S2A_MSIL2A_20240425T042711_N0510_R133_T46RCP_20240425T090051.SAFE",
    },
    # T2 for Assam/Bihar Sep 7 is ALREADY downloaded — skip it
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
        raise SystemExit("Set CDSE_USER and CDSE_PASS")

    token = get_token(username, password)

    for target in TARGETS:
        cache_dir = DATA_DIR / target["region"]
        cache_dir.mkdir(parents=True, exist_ok=True)
        out_path = cache_dir / f"{target['which']}_{target['date']}.tif"
        log.info("Fetching %s/%s -> %s", target["region"], target["which"], out_path.name)
        product = fetch_by_name(target["name"], token)
        ok = download_and_extract(product, token, target["bbox"], out_path)
        log.info("✓ done" if ok else "✗ failed")

if __name__ == "__main__":
    main()
