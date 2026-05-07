"""Google Cloud Storage integration for image uploads."""
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)

_client = None
LOCAL_IMAGE_ROOT = Path("/tmp/campus_monitor")


def _get_client():
    global _client
    if _client is None:
        from google.cloud import storage
        _client = storage.Client(project=settings.GOOGLE_CLOUD_PROJECT_ID)
    return _client


def upload_image(
    image_bytes: bytes,
    device_id: int,
    file_extension: str = "jpg",
) -> str:
    """
    Upload image bytes to Cloud Storage and return the public URL.

    Images are organized as: {device_id}/{date}/{uuid}.{ext}

    Falls back to a local file path if GCP is not configured.
    """
    if not settings.GOOGLE_CLOUD_STORAGE_BUCKET:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        file_name = f"{uuid.uuid4().hex[:12]}.{file_extension}"
        local_dir = LOCAL_IMAGE_ROOT / str(device_id) / date_str
        local_dir.mkdir(parents=True, exist_ok=True)
        local_path = local_dir / file_name
        local_path.write_bytes(image_bytes)
        logger.warning(
            "GCP bucket not configured - saved image locally at %s",
            local_path,
        )
        return local_path.resolve().as_uri()

    client = _get_client()
    bucket = client.bucket(settings.GOOGLE_CLOUD_STORAGE_BUCKET)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    blob_name = f"{device_id}/{date_str}/{uuid.uuid4().hex[:12]}.{file_extension}"
    blob = bucket.blob(blob_name)

    blob.upload_from_string(image_bytes, content_type="image/jpeg")
    url = blob.public_url
    try:
        blob.make_public()
    except Exception as exc:
        logger.warning(
            "Uploaded image to GCS but could not make it public. "
            "This usually means uniform bucket-level access is enabled: %s",
            exc,
        )

    logger.info(f"Uploaded image to GCS: {url}")
    return url


def read_image_bytes(image_url: str) -> bytes:
    """Read image bytes from either local fallback storage or GCS."""
    if image_url.startswith("file://"):
        local_path = Path(image_url.removeprefix("file://"))
        return local_path.read_bytes()

    object_name = extract_object_name(image_url)
    if not object_name:
        raise ValueError("Unsupported image URL")

    client = _get_client()
    bucket = client.bucket(settings.GOOGLE_CLOUD_STORAGE_BUCKET)
    blob = bucket.blob(object_name)
    return blob.download_as_bytes()


def delete_image(object_name: str) -> bool:
    """Delete an image from Cloud Storage. Returns True if deleted."""
    if not settings.GOOGLE_CLOUD_STORAGE_BUCKET:
        return False

    try:
        if object_name.startswith("file://"):
            local_path = Path(object_name.removeprefix("file://"))
            if local_path.exists():
                local_path.unlink()
            return True

        client = _get_client()
        bucket = client.bucket(settings.GOOGLE_CLOUD_STORAGE_BUCKET)
        blob = bucket.blob(object_name)
        blob.delete()
        logger.info(f"Deleted image from GCS: {object_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete GCS image: {e}")
        return False


def extract_object_name(image_url: str) -> Optional[str]:
    """Extract the GCS object name from a public URL."""
    if image_url.startswith("file://"):
        return image_url

    bucket_name = settings.GOOGLE_CLOUD_STORAGE_BUCKET
    prefix = f"https://storage.googleapis.com/{bucket_name}/"
    if image_url.startswith(prefix):
        return image_url[len(prefix):]
    return None
