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
from typing import Optional

import requests

# Camera library - use picamera2 on Raspberry Pi OS
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
        logger.warning("No camera detected - generating dummy image for testing")
        # Create a tiny valid JPEG for testing the pipeline
        from PIL import Image
        buf = io.BytesIO()
        Image.new("RGB", (640, 480), color=(100, 150, 200)).save(buf, format="JPEG")
        return buf.getvalue()

    from PIL import Image
    raise RuntimeError("capture_image requires an initialized camera on Raspberry Pi")


def init_camera() -> Optional["Picamera2"]:
    """Create and start one camera session for the lifetime of the script."""
    if not HAS_CAMERA:
        return None

    camera = Picamera2()
    config = camera.create_still_configuration(
        main={"format": "RGB888"},
        buffer_count=2,
    )
    camera.configure(config)
    camera.start()
    # Let the sensor and auto-controls settle before the first capture.
    time.sleep(2)
    logger.info("Camera initialized.")
    return camera


def close_camera(camera: Optional["Picamera2"]) -> None:
    """Stop and close the camera cleanly."""
    if camera is None:
        return

    try:
        camera.stop()
    except Exception:
        logger.debug("Camera stop raised during cleanup.", exc_info=True)

    try:
        camera.close()
    except Exception:
        logger.debug("Camera close raised during cleanup.", exc_info=True)


def capture_image_from_camera(camera: "Picamera2") -> bytes:
    """Capture one frame from an already-running camera and return JPEG bytes."""
    from PIL import Image

    array = camera.capture_array("main")
    image = Image.fromarray(array).convert("RGB")
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
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
            logger.info(f"Image uploaded: id={data['image_id']}")
            return True
        else:
            logger.error(f"Upload failed ({resp.status_code}): {resp.text}")
            return False
    except requests.RequestException as e:
        logger.error(f"Connection error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Raspberry Pi image capture script")
    parser.add_argument("--backend", required=True, help="FastAPI backend URL (e.g., http://192.168.1.100:8000)")
    parser.add_argument("--device-id", type=int, required=True, help="Device ID registered in the backend")
    parser.add_argument("--interval", type=int, default=60, help="Capture interval in seconds (default: 60)")
    args = parser.parse_args()

    logger.info(
        f"Starting capture - backend={args.backend}, "
        f"device_id={args.device_id}, interval={args.interval}s"
    )
    camera = None

    if not HAS_CAMERA:
        logger.warning("picamera2 not available - running in test mode (dummy images)")
    else:
        camera = init_camera()

    try:
        while True:
            logger.info("Capturing image...")
            try:
                if HAS_CAMERA:
                    image_bytes = capture_image_from_camera(camera)
                else:
                    image_bytes = capture_image()
                send_to_backend(image_bytes, args.backend, args.device_id)
            except Exception as e:
                logger.error(f"Capture error: {e}")
                if HAS_CAMERA:
                    logger.info("Resetting camera before the next capture attempt...")
                    close_camera(camera)
                    camera = init_camera()

            logger.info(f"Next capture in {args.interval}s...")
            time.sleep(args.interval)
    finally:
        close_camera(camera)


if __name__ == "__main__":
    main()
