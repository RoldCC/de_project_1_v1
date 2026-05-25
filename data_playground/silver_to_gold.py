import logging
import os
import sys
import tempfile
from io import BytesIO

import pyarrow as pa
import pyarrow.parquet as pq
from dotenv import load_dotenv
from pyspark.sql import SparkSession, Window
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

def read_silver(spark: SparkSession):
    client = get_blob_service_client()
    data = client.get_blob_client("silver", "silver_data.parquet").download_blob().readall()
    pandas_df = pq.read_table(BytesIO(data)).to_pandas()
    logger.info("Silver loaded: %d rows, %d cols", len(pandas_df), len(pandas_df.columns))
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
# Dimension tables (native PySpark — no UDFs)
# =========================================================

def build_dim_game(silver):
    # 2NF/3NF: all non-key attributes depend only on game_id
    return (
        silver
        .select("id", "slug", "name", "released", "tba", "esrb_name")
        .distinct()
        .withColumnRenamed("id", "game_id")
    )


def build_dim_genre(silver):
    return (
        silver
        .select("genre_name")
        .filter(F.col("genre_name").isNotNull())
        .distinct()
        .withColumn("genre_id", F.row_number().over(Window.orderBy("genre_name")))
        .select("genre_id", "genre_name")
    )


def build_dim_platform(silver):
    return (
        silver
        .select("platform_name")
        .filter(F.col("platform_name").isNotNull())
        .distinct()
        .withColumn("platform_id", F.row_number().over(Window.orderBy("platform_name")))
        .select("platform_id", "platform_name")
    )


def build_dim_store(silver):
    return (
        silver
        .select("store_name")
        .filter(F.col("store_name").isNotNull())
        .distinct()
        .withColumn("store_id", F.row_number().over(Window.orderBy("store_name")))
        .select("store_id", "store_name")
    )


# =========================================================
# Fact tables
# =========================================================

def build_fact_game_metrics(silver):
    # One row per game — DISTINCT removes duplicates introduced by the 1NF explosion
    return (
        silver
        .select("id", "rating", "ratings_count", "reviews_text_count", "added", "playtime", "reviews_count")
        .distinct()
        .withColumnRenamed("id", "game_id")
    )


def build_fact_game_genre(silver, dim_genre):
    return (
        silver
        .select(F.col("id").alias("game_id"), "genre_name")
        .filter(F.col("genre_name").isNotNull())
        .distinct()
        .join(dim_genre, "genre_name", "left")
        .select("game_id", "genre_id")
    )


def build_fact_game_platform(silver, dim_platform):
    return (
        silver
        .select(F.col("id").alias("game_id"), "platform_name")
        .filter(F.col("platform_name").isNotNull())
        .distinct()
        .join(dim_platform, "platform_name", "left")
        .select("game_id", "platform_id")
    )


def build_fact_game_store(silver, dim_store):
    return (
        silver
        .select(F.col("id").alias("game_id"), "store_name")
        .filter(F.col("store_name").isNotNull())
        .distinct()
        .join(dim_store, "store_name", "left")
        .select("game_id", "store_id")
    )


# =========================================================
# Main
# =========================================================

def main() -> None:
    spark = get_spark()

    silver = read_silver(spark)
    silver.cache()

    logger.info("Building dimension tables...")
    dim_genre    = build_dim_genre(silver).cache()
    dim_platform = build_dim_platform(silver).cache()
    dim_store    = build_dim_store(silver).cache()

    tables = {
        "dim_game.parquet":            build_dim_game(silver),
        "dim_genre.parquet":           dim_genre,
        "dim_platform.parquet":        dim_platform,
        "dim_store.parquet":           dim_store,
        "fact_game_metrics.parquet":   build_fact_game_metrics(silver),
        "fact_game_genre.parquet":     build_fact_game_genre(silver, dim_genre),
        "fact_game_platform.parquet":  build_fact_game_platform(silver, dim_platform),
        "fact_game_store.parquet":     build_fact_game_store(silver, dim_store),
    }

    logger.info("Writing %d gold tables...", len(tables))
    for blob_name, df in tables.items():
        write_gold(df, blob_name)

    spark.stop()
    logger.info("Gold layer complete.")


if __name__ == "__main__":
    main()
