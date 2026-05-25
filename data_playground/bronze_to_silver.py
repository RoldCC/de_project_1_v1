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
from pyspark.sql.types import (
    ArrayType, IntegerType, StringType, StructField, StructType,
)

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from data_environment_structure.utils import get_blob_service_client, upload_to_layer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# =========================================================
# Config
# =========================================================

DROP_COLS = {
    "user_game", "clip", "saturated_color", "dominant_color",
    "short_screenshots", "metacritic", "suggestions_count", "updated",
    "rating_top", "background_image", "parent_platforms", "added_by_status",
    "ratings", "tags",
}

# Minimal schemas — only fields we keep
GENRE_SCHEMA = ArrayType(StructType([
    StructField("name", StringType()),
]))

PLATFORM_SCHEMA = ArrayType(StructType([
    StructField("platform", StructType([
        StructField("name", StringType()),
    ])),
]))

STORE_SCHEMA = ArrayType(StructType([
    StructField("store", StructType([
        StructField("name", StringType()),
    ])),
]))


# =========================================================
# Spark
# =========================================================

def get_spark() -> SparkSession:
    spark = (
        SparkSession.builder
        .appName("bronze_to_silver")
        .master("local[*]")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


# =========================================================
# I/O
# =========================================================

def read_bronze(spark: SparkSession):
    client = get_blob_service_client()
    data = client.get_blob_client("bronze", "bronze_data.parquet").download_blob().readall()
    pandas_df = pq.read_table(BytesIO(data)).to_pandas()
    # Drop all-null columns before Spark schema inference (Spark can't determine type for fully-null columns)
    pandas_df = pandas_df.dropna(axis=1, how="all")
    logger.info("Bronze loaded: %d rows, %d cols", len(pandas_df), len(pandas_df.columns))
    return spark.createDataFrame(pandas_df)


def write_silver(df) -> None:
    pandas_df = df.toPandas()
    table = pa.Table.from_pandas(pandas_df)
    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
        pq.write_table(table, tmp.name)
        tmp_path = tmp.name
    try:
        upload_to_layer(tmp_path, "silver", "silver_data.parquet")
        size_mb = os.path.getsize(tmp_path) / 1e6
        logger.info("silver_data.parquet uploaded — %.2f MB", size_mb)
    finally:
        os.unlink(tmp_path)


# =========================================================
# Transformations (native PySpark only — no UDFs)
# =========================================================

def transform(df):
    # Drop unwanted columns
    to_drop = [c for c in df.columns if c in DROP_COLS]
    df = df.drop(*to_drop)
    logger.info("Dropped %d columns: %s", len(to_drop), to_drop)

    # Parse JSON string arrays → extract name, then explode to 1NF (one row per game × genre × platform × store)
    df = df.withColumn(
        "genre_name",
        F.explode(F.transform(F.from_json(F.col("genres"), GENRE_SCHEMA), lambda x: x["name"])),
    )
    df = df.withColumn(
        "platform_name",
        F.explode(F.transform(F.from_json(F.col("platforms"), PLATFORM_SCHEMA), lambda x: x["platform"]["name"])),
    )
    df = df.withColumn(
        "store_name",
        F.explode(F.transform(F.from_json(F.col("stores"), STORE_SCHEMA), lambda x: x["store"]["name"])),
    )

    # Parse esrb_rating dict → single name string
    df = df.withColumn("esrb_name", F.get_json_object(F.col("esrb_rating"), "$.name"))

    # Drop original JSON string columns
    df = df.drop("genres", "platforms", "stores", "esrb_rating")

    # Cast released to DateType (ISO 8601 yyyy-MM-dd)
    df = df.withColumn("released", F.to_date(F.col("released"), "yyyy-MM-dd"))

    # Standardize nulls: empty / whitespace-only strings → null
    str_cols = [f.name for f in df.schema.fields if isinstance(f.dataType, StringType)]
    for col_name in str_cols:
        df = df.withColumn(
            col_name,
            F.when(F.trim(F.col(col_name)) == "", None).otherwise(F.col(col_name)),
        )

    # NaN → null for float columns
    float_cols = [f.name for f in df.schema.fields if str(f.dataType) == "DoubleType()"]
    for col_name in float_cols:
        df = df.withColumn(
            col_name,
            F.when(F.isnan(F.col(col_name)), None).otherwise(F.col(col_name)),
        )

    return df


# =========================================================
# Dedup
# =========================================================

def dedup(df):
    before = df.count()
    df = df.dropDuplicates(["id", "genre_name", "platform_name", "store_name"])
    after = df.count()
    dupes = before - after
    if dupes:
        logger.warning("Removed %d duplicate game IDs", dupes)
    else:
        logger.info("No duplicates found (%d rows)", before)
    return df


# =========================================================
# Main
# =========================================================

def main() -> None:
    spark = get_spark()

    df = read_bronze(spark)
    df = transform(df)
    df = dedup(df)

    logger.info("Silver schema:")
    df.printSchema()
    logger.info("Silver row count: %d", df.count())

    write_silver(df)
    spark.stop()


if __name__ == "__main__":
    main()
