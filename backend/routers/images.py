"""Endpoints for image upload, listing, and deletion."""
import logging
import mimetypes
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response

from database import get_connection
from models import ImageResponse
from services.storage import (
    delete_image as gcs_delete,
    extract_object_name,
    read_image_bytes,
    upload_image,
)
from services.vision import detect_objects

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/images", tags=["Images"])


def _row_to_image(row) -> ImageResponse:
    return ImageResponse(**dict(row))


def _guess_media_type(file_name: str | None, image_url: str) -> str:
    media_type, _ = mimetypes.guess_type(file_name or image_url)
    return media_type or "image/jpeg"


@router.post("/upload", status_code=201, response_model=ImageResponse)
def upload_and_detect(
    device_id: int = Form(..., description="Device ID for the uploaded image"),
    file: UploadFile = File(..., description="Image file to upload"),
):
    """
    Upload an image, store it in GCS, run Vision API detection,
    and save all results to the database.
    """
    conn = get_connection()

    # Verify device exists
    device = conn.execute(
        "SELECT device_id FROM devices WHERE device_id = ?", (device_id,)
    ).fetchone()
    if not device:
        conn.close()
        raise HTTPException(status_code=404, detail="Device not found")

    try:
        # Read image bytes
        image_bytes = file.file.read()

        # Upload to GCS
        ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "jpg"
        image_url = upload_image(image_bytes, device_id, ext)

        # Store image record
        cur = conn.execute(
            """INSERT INTO images (device_id, image_url, file_name)
               VALUES (?, ?, ?)""",
            (device_id, image_url, file.filename),
        )
        conn.commit()
        image_id = cur.lastrowid

        # Run object detection
        try:
            detections = detect_objects(image_bytes)

            for det in detections:
                conn.execute(
                    """INSERT INTO detections (image_id, device_id, object_label, confidence)
                       VALUES (?, ?, ?, ?)""",
                    (image_id, device_id, det["label"], det["confidence"]),
                )
            conn.commit()
            logger.info(f"Saved {len(detections)} detections for image {image_id}")
        except Exception as e:
            logger.error(f"Vision API failed for image {image_id}: {e}")
            # Image is still stored, just no detections

        row = conn.execute(
            "SELECT * FROM images WHERE image_id = ?", (image_id,)
        ).fetchone()
        return _row_to_image(row)

    finally:
        conn.close()


@router.get("/", response_model=list[ImageResponse])
def list_images(
    device_id: int = None,
    limit: int = 50,
    offset: int = 0,
):
    """List stored image records with metadata."""
    conn = get_connection()
    try:
        if device_id:
            rows = conn.execute(
                """SELECT * FROM images WHERE device_id = ?
                   ORDER BY captured_at DESC LIMIT ? OFFSET ?""",
                (device_id, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT * FROM images ORDER BY captured_at DESC LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()
        return [_row_to_image(r) for r in rows]
    finally:
        conn.close()


@router.get("/{image_id}", response_model=ImageResponse)
def get_image(image_id: int):
    """Retrieve metadata and Cloud Storage URL for an image."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM images WHERE image_id = ?", (image_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Image not found")
        return _row_to_image(row)
    finally:
        conn.close()


@router.get("/{image_id}/content", include_in_schema=False)
def get_image_content(image_id: int):
    """Serve image content for dashboard previews."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT image_url, file_name FROM images WHERE image_id = ?", (image_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Image not found")

        image_url = row["image_url"]
        file_name = row["file_name"]
        media_type = _guess_media_type(file_name, image_url)

        if image_url.startswith("file://"):
            local_path = Path(image_url.removeprefix("file://"))
            if not local_path.exists():
                raise HTTPException(status_code=404, detail="Image file not found")
            return FileResponse(local_path, media_type=media_type, filename=file_name)

        try:
            image_bytes = read_image_bytes(image_url)
        except Exception as exc:
            logger.error("Failed to load image content for %s: %s", image_id, exc)
            raise HTTPException(status_code=404, detail="Image content unavailable") from exc

        return Response(content=image_bytes, media_type=media_type)
    finally:
        conn.close()


@router.delete("/{image_id}", status_code=204)
def delete_image_record(image_id: int):
    """Delete image record and the file from Cloud Storage."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM images WHERE image_id = ?", (image_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Image not found")

        # Delete from GCS
        image_url = dict(row)["image_url"]
        object_name = extract_object_name(image_url)
        if object_name:
            gcs_delete(object_name)

        # Detections cascade-deleted via foreign key
        conn.execute("DELETE FROM images WHERE image_id = ?", (image_id,))
        conn.commit()
    finally:
        conn.close()
