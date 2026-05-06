"""Google Cloud Vision API integration."""
import logging

from config import settings

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        from google.cloud import vision
        _client = vision.ImageAnnotatorClient()
    return _client


def detect_objects(image_bytes: bytes) -> list[dict]:
    """
    Send image bytes to Cloud Vision API and return detected objects.

    Returns list of dicts with keys: label, confidence.
    """
    if not settings.GOOGLE_CLOUD_PROJECT_ID:
        logger.warning("GCP project not configured - skipping Vision API")
        return []

    from google.cloud import vision

    client = _get_client()

    try:
        image = vision.Image(content=image_bytes)
        response = client.label_detection(image=image)
        labels = response.label_annotations

        results = []
        for label in labels:
            results.append({
                "label": label.description,
                "confidence": label.score,
            })

        logger.info(f"Vision API returned {len(results)} labels")
        return results

    except Exception as e:
        logger.error(f"Vision API error: {e}")
        raise


def detect_objects_from_file(file_path: str) -> list[dict]:
    """Read a local file and run detection."""
    with open(file_path, "rb") as f:
        return detect_objects(f.read())
