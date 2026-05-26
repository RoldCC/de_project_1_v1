import logging
import os
import sys
import tempfile
from io import BytesIO

import pyarrow as pa
import pyarrow.parquet as pq
from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_environment_structure.utils import get_blob_service_client, upload_to_layer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# =========================================================
# Spark
# =========================================================

def get_spark() -> SparkSession:
    spark = (
        SparkSession.builder
        .appName("silver_to_gold")
        .master("local[*]")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


# =========================================================
# I/O
# =========================================================

def read_silver_table(spark: SparkSession, blob_name: str):
    client = get_blob_service_client()
    data = client.get_blob_client("silver", blob_name).download_blob().readall()
    pandas_df = pq.read_table(BytesIO(data)).to_pandas()
    logger.info("Loaded silver/%s — %d rows", blob_name, len(pandas_df))
    return spark.createDataFrame(pandas_df)


def write_gold(df, blob_name: str) -> None:
    row_count = df.count()
    pandas_df = df.toPandas()
    table = pa.Table.from_pandas(pandas_df)
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        pq.write_table(table, tmp.name)
        tmp_path = tmp.name
    try:
        upload_to_layer(tmp_path, "gold", blob_name)
        size_mb = os.path.getsize(tmp_path) / 1e6
        logger.info("%s — %d rows, %.2f MB", blob_name, row_count, size_mb)
    finally:
        os.unlink(tmp_path)


# =========================================================
# Gold tables (denormalized for dashboard — no ID lookups needed)
# =========================================================

def build_gold_games(dim_games, fact_metrics):
    # One row per game: attributes + metrics joined, IDs and slug dropped (not needed by dashboard)
    return (
        dim_games
        .join(fact_metrics, "game_id", "inner")
        .select(
            "game_id", "name", "released", "esrb_name",
            "rating", "playtime", "ratings_count", "reviews_text_count",
            "reviews_count", "added",
        )
    )


def build_gold_game_genres(fact_genre, dim_genre):
    # Names pre-joined — dashboard queries avoid extra dim table lookups
    return (
        fact_genre
        .join(dim_genre, "genre_id", "inner")
        .select("game_id", "genre_name")
    )


def build_gold_game_platforms(fact_platform, dim_platform):
    return (
        fact_platform
        .join(dim_platform, "platform_id", "inner")
        .select("game_id", "platform_name")
    )


def build_gold_game_stores(fact_store, dim_store):
    return (
        fact_store
        .join(dim_store, "store_id", "inner")
        .select("game_id", "store_name")
    )


# =========================================================
# Main
# =========================================================

def main() -> None:
    spark = get_spark()

    # Read silver normalized tables
    dim_games     = read_silver_table(spark, "silver_dim_games.parquet").cache()
    dim_genre     = read_silver_table(spark, "silver_dim_genre.parquet").cache()
    dim_platform  = read_silver_table(spark, "silver_dim_platform.parquet").cache()
    dim_store     = read_silver_table(spark, "silver_dim_store.parquet").cache()
    fact_metrics  = read_silver_table(spark, "silver_fact_game_metrics.parquet").cache()
    fact_genre    = read_silver_table(spark, "silver_fact_game_genre.parquet").cache()
    fact_platform = read_silver_table(spark, "silver_fact_game_platform.parquet").cache()
    fact_store    = read_silver_table(spark, "silver_fact_game_store.parquet").cache()

    tables = {
        "gold_games.parquet":          build_gold_games(dim_games, fact_metrics),
        "gold_game_genres.parquet":    build_gold_game_genres(fact_genre, dim_genre),
        "gold_game_platforms.parquet": build_gold_game_platforms(fact_platform, dim_platform),
        "gold_game_stores.parquet":    build_gold_game_stores(fact_store, dim_store),
    }

    logger.info("Writing %d gold tables...", len(tables))
    for blob_name, df in tables.items():
        write_gold(df, blob_name)

    spark.stop()
    logger.info("Gold layer complete.")


if __name__ == "__main__":
    main()
