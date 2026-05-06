"""Google Cloud Storage integration for image uploads."""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)

_client = None


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
        logger.warning("GCP bucket not configured - returning local placeholder URL")
        return f"file:///tmp/campus_monitor/{device_id}/{uuid.uuid4().hex[:12]}.{file_extension}"

    client = _get_client()
    bucket = client.bucket(settings.GOOGLE_CLOUD_STORAGE_BUCKET)

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    blob_name = f"{device_id}/{date_str}/{uuid.uuid4().hex[:12]}.{file_extension}"
    blob = bucket.blob(blob_name)

    blob.upload_from_string(image_bytes, content_type="image/jpeg")
    blob.make_public()

    url = blob.public_url
    logger.info(f"Uploaded image to GCS: {url}")
    return url


def delete_image(object_name: str) -> bool:
    """Delete an image from Cloud Storage. Returns True if deleted."""
    if not settings.GOOGLE_CLOUD_STORAGE_BUCKET:
        return False

    try:
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
    bucket_name = settings.GOOGLE_CLOUD_STORAGE_BUCKET
    prefix = f"https://storage.googleapis.com/{bucket_name}/"
    if image_url.startswith(prefix):
        return image_url[len(prefix):]
    return None
