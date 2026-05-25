import json
import logging
import os
import sys
import tempfile
import time

import pyarrow as pa
import pyarrow.parquet as pq
import requests
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_environment_structure.utils import upload_to_layer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# =========================================================
# Config
# =========================================================

RAWG_API_KEY = os.getenv("RAWG_API_KEY")
BASE_URL = "https://api.rawg.io/api/games"
TOTAL_PAGES = 400
PAGE_SIZE = 40
REQUEST_DELAY = 0.1   # 10 req/s — comfortably under the 20 req/s limit
MAX_RETRIES = 5


# =========================================================
# Fetch
# =========================================================

def fetch_page(session: requests.Session, page: int) -> list[dict]:
    params = {"key": RAWG_API_KEY, "page": page, "page_size": PAGE_SIZE}
    backoff = 2.0
    for attempt in range(MAX_RETRIES):
        try:
            resp = session.get(BASE_URL, params=params, timeout=30)
        except requests.RequestException as exc:
            logger.warning("Network error page %d attempt %d: %s", page, attempt + 1, exc)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
            continue

        if resp.status_code == 200:
            return resp.json().get("results", [])
        elif resp.status_code == 429:
            logger.warning("Rate limited on page %d — backing off %.1fs", page, backoff)
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
        else:
            resp.raise_for_status()

    raise RuntimeError(f"Failed to fetch page {page} after {MAX_RETRIES} attempts")


# =========================================================
# Serialization
# =========================================================

def serialize_nested(records: list[dict]) -> list[dict]:
    """Serialize dict/list values to JSON strings for bronze layer storage."""
    result = []
    for row in records:
        result.append({
            k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
            for k, v in row.items()
        })
    return result


# =========================================================
# Parquet
# =========================================================

def records_to_parquet_bytes(records: list[dict]) -> bytes:
    table = pa.Table.from_pylist(records)
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        pq.write_table(table, tmp_path)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp_path)


# =========================================================
# Main
# =========================================================

def main() -> None:
    if not RAWG_API_KEY:
        raise EnvironmentError("RAWG_API_KEY not set in .env")

    logger.info("Starting extraction — %d pages × %d rows", TOTAL_PAGES, PAGE_SIZE)

    session = requests.Session()
    all_records: list[dict] = []

    for page in range(1, TOTAL_PAGES + 1):
        records = fetch_page(session, page)
        if not records:
            logger.warning("Empty response on page %d — stopping early", page)
            break
        all_records.extend(serialize_nested(records))

        if page % 50 == 0:
            logger.info("Progress: %d/%d pages — %d records", page, TOTAL_PAGES, len(all_records))

        time.sleep(REQUEST_DELAY)

    logger.info("Fetched %d total records", len(all_records))
    logger.info("Serializing to parquet...")

    parquet_bytes = records_to_parquet_bytes(all_records)

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        tmp.write(parquet_bytes)
        tmp_path = tmp.name

    try:
        upload_to_layer(tmp_path, "bronze", "bronze_data.parquet")
        logger.info("bronze_data.parquet uploaded to Azurite bronze layer — %.2f MB", len(parquet_bytes) / 1e6)
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    main()
