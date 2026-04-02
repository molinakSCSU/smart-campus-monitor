"""
Raspberry Pi Image Capture Script

Captures images at a regular interval from the Pi camera
and sends them to the FastAPI backend for processing.

Usage:
    python capture.py --backend http://YOUR_SERVER:8000 --device-id 1 --interval 60
"""
import argparse
import io
import logging
import time
from datetime import datetime

import requests

# Camera library — use picamera2 on Raspberry Pi OS
# Falls back to a dummy capture for testing on non-Pi systems
try:
    from picamera2 import Picamera2
    HAS_CAMERA = True
except ImportError:
    HAS_CAMERA = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def capture_image():
    """Capture a single frame from the Pi camera."""
    if not HAS_CAMERA:
        logger.warning("No camera detected — generating dummy image for testing")
        # Create a tiny valid JPEG for testing the pipeline
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (640, 480), color=(100, 150, 200)).save(buf, format="JPEG")
        return buf.getvalue()

    camera = Picamera2()
    camera.start()
    # Let the camera warm up
    time.sleep(2)
    array = camera.capture_array("main")
    camera.stop()

    from PIL import Image
    buf = io.BytesIO()
    Image.fromarray(array).save(buf, format="JPEG")
    return buf.getvalue()


def send_to_backend(image_bytes: bytes, backend_url: str, device_id: int) -> bool:
    """POST image to the FastAPI backend /images/upload endpoint."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"capture_{timestamp}.jpg"

    try:
        resp = requests.post(
            f"{backend_url}/images/upload",
            files={"file": (filename, image_bytes, "image/jpeg")},
            data={"device_id": str(device_id)},
            timeout=60,
        )
        if resp.ok:
            data = resp.json()
            logger.info(f"✅ Image uploaded: ID={data['image_id']}")
            return True
        else:
            logger.error(f"❌ Upload failed ({resp.status_code}): {resp.text}")
            return False
    except requests.RequestException as e:
        logger.error(f"❌ Connection error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Raspberry Pi image capture script")
    parser.add_argument("--backend", required=True, help="FastAPI backend URL (e.g., http://192.168.1.100:8000)")
    parser.add_argument("--device-id", type=int, required=True, help="Device ID registered in the backend")
    parser.add_argument("--interval", type=int, default=60, help="Capture interval in seconds (default: 60)")
    args = parser.parse_args()

    logger.info(f"Starting capture — backend={args.backend}, device_id={args.device_id}, interval={args.interval}s")
    if not HAS_CAMERA:
        logger.warning("picamera2 not available — running in test mode (dummy images)")

    while True:
        logger.info("Capturing image...")
        try:
            image_bytes = capture_image()
            send_to_backend(image_bytes, args.backend, args.device_id)
        except Exception as e:
            logger.error(f"Capture error: {e}")

        logger.info(f"Next capture in {args.interval}s...")
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
