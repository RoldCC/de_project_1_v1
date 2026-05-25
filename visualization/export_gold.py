import logging
import os
import sys
from io import BytesIO

import pyarrow.parquet as pq
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_environment_structure.utils import get_blob_service_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# =========================================================
# Config
# =========================================================

TABLES = [
    "dim_game",
    "dim_genre",
    "dim_platform",
    "dim_store",
    "fact_game_metrics",
    "fact_game_genre",
    "fact_game_platform",
    "fact_game_store",
]

DEST_DIR = os.path.join(os.path.dirname(__file__), "sources", "gold_data")


# =========================================================
# Main
# =========================================================

def main() -> None:
    client = get_blob_service_client()
    os.makedirs(DEST_DIR, exist_ok=True)

    for table in TABLES:
        blob_name = f"{table}.parquet"
        dest_path = os.path.join(DEST_DIR, blob_name)

        data = client.get_blob_client("gold", blob_name).download_blob().readall()
        arrow_table = pq.read_table(BytesIO(data))
        pq.write_table(arrow_table, dest_path)

        size_kb = os.path.getsize(dest_path) / 1e3
        logger.info("%s — %d rows, %.1f KB", table, len(arrow_table), size_kb)

    logger.info("All gold parquet files saved to %s", DEST_DIR)


if __name__ == "__main__":
    main()
