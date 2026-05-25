import logging
import os
from pathlib import Path

from azure.storage.blob import BlobServiceClient, ContainerClient
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# =========================================================
# Client
# =========================================================

def get_blob_service_client() -> BlobServiceClient:
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn_str:
        raise EnvironmentError("AZURE_STORAGE_CONNECTION_STRING not set in .env")
    return BlobServiceClient.from_connection_string(conn_str)


# =========================================================
# Container operations
# =========================================================

def create_container(container_name: str) -> None:
    client = get_blob_service_client()
    try:
        client.create_container(container_name)
        logger.info("Container created: %s", container_name)
    except Exception as e:
        # 409 = already exists — safe to ignore
        if "ContainerAlreadyExists" in str(e):
            logger.info("Container already exists: %s", container_name)
        else:
            raise


# =========================================================
# File operations
# =========================================================

def upload_file(container_name: str, blob_name: str, local_path: str) -> None:
    client = get_blob_service_client()
    with open(local_path, "rb") as f:
        client.get_blob_client(container=container_name, blob=blob_name).upload_blob(f, overwrite=True)
    logger.info("Uploaded %s → %s/%s", local_path, container_name, blob_name)


def download_file(container_name: str, blob_name: str, dest_path: str) -> None:
    client = get_blob_service_client()
    Path(dest_path).parent.mkdir(parents=True, exist_ok=True)
    blob = client.get_blob_client(container=container_name, blob=blob_name)
    with open(dest_path, "wb") as f:
        f.write(blob.download_blob().readall())
    logger.info("Downloaded %s/%s → %s", container_name, blob_name, dest_path)


def upload_to_layer(local_path: str, layer: str, blob_name: str) -> None:
    """Upload a file to a medallion layer container (bronze / silver / gold)."""
    valid_layers = {"bronze", "silver", "gold"}
    if layer not in valid_layers:
        raise ValueError(f"layer must be one of {valid_layers}, got '{layer}'")
    create_container(layer)
    upload_file(layer, blob_name, local_path)


# =========================================================
# Main
# =========================================================

def main() -> None:
    logger.info("Testing Azurite connection...")
    client = get_blob_service_client()
    containers = [c["name"] for c in client.list_containers()]
    logger.info("Existing containers: %s", containers or "(none)")
    logger.info("Connection OK")


if __name__ == "__main__":
    main()
