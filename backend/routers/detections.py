"""CRUD endpoints for detections."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from database import get_connection
from models import DetectionCreate, DetectionDetail, DetectionResponse, DetectionUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/detections", tags=["Detections"])


def _row_to_detection(row) -> DetectionResponse:
    return DetectionResponse(**dict(row))


def _row_to_detail(row) -> DetectionDetail:
    return DetectionDetail(**dict(row))


@router.post("/", response_model=DetectionResponse, status_code=201)
def create_detection(body: DetectionCreate):
    """Create a new detection record."""
    conn = get_connection()
    try:
        # Verify image exists
        img = conn.execute(
            "SELECT image_id FROM images WHERE image_id = ?", (body.image_id,)
        ).fetchone()
        if not img:
            raise HTTPException(status_code=404, detail="Image not found")

        cur = conn.execute(
            """INSERT INTO detections (image_id, device_id, object_label, confidence)
               VALUES (?, ?, ?, ?)""",
            (body.image_id, body.device_id, body.object_label, body.confidence),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM detections WHERE detection_id = ?", (cur.lastrowid,)
        ).fetchone()
        return _row_to_detection(row)
    finally:
        conn.close()


@router.get("/", response_model=list[DetectionDetail])
def list_detections(
    object_label: Optional[str] = Query(None, description="Filter by object type"),
    min_confidence: Optional[float] = Query(None, ge=0, le=1, description="Minimum confidence score"),
    device_id: Optional[int] = Query(None, description="Filter by device"),
    hours: Optional[int] = Query(None, description="Limit to last N hours"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """List detections with optional filters. Returns enriched data with device + image info."""
    conn = get_connection()
    try:
        query = """
            SELECT d.detection_id, d.object_label, d.confidence, d.detected_at,
                   dev.device_name, dev.location, img.image_url
            FROM detections d
            JOIN images img ON d.image_id = img.image_id
            JOIN devices dev ON d.device_id = dev.device_id
            WHERE 1=1
        """
        params: list = []

        if object_label:
            query += " AND d.object_label = ?"
            params.append(object_label)
        if min_confidence is not None:
            query += " AND d.confidence >= ?"
            params.append(min_confidence)
        if device_id is not None:
            query += " AND d.device_id = ?"
            params.append(device_id)
        if hours is not None:
            query += " AND d.detected_at >= datetime('now', ?)"
            params.append(f"-{hours} hours")

        query += " ORDER BY d.detected_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return [_row_to_detail(r) for r in rows]
    finally:
        conn.close()


@router.get("/{detection_id}", response_model=DetectionDetail)
def get_detection(detection_id: int):
    """Retrieve a specific detection with device and image info."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT d.detection_id, d.object_label, d.confidence, d.detected_at,
                   dev.device_name, dev.location, img.image_url
            FROM detections d
            JOIN images img ON d.image_id = img.image_id
            JOIN devices dev ON d.device_id = dev.device_id
            WHERE d.detection_id = ?
            """,
            (detection_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Detection not found")
        return _row_to_detail(row)
    finally:
        conn.close()


@router.put("/{detection_id}", response_model=DetectionResponse)
def update_detection(detection_id: int, body: DetectionUpdate):
    """Update a detection (label, annotation/confidence)."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM detections WHERE detection_id = ?", (detection_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Detection not found")

        updates = []
        params = []
        if body.object_label is not None:
            updates.append("object_label = ?")
            params.append(body.object_label)
        if body.confidence is not None:
            updates.append("confidence = ?")
            params.append(body.confidence)

        if not updates:
            return _row_to_detection(row)

        params.append(detection_id)
        conn.execute(
            f"UPDATE detections SET {', '.join(updates)} WHERE detection_id = ?",
            params,
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM detections WHERE detection_id = ?", (detection_id,)
        ).fetchone()
        return _row_to_detection(row)
    finally:
        conn.close()


@router.delete("/{detection_id}", status_code=204)
def delete_detection(detection_id: int):
    """Delete a detection record."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM detections WHERE detection_id = ?", (detection_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Detection not found")
        conn.execute(
            "DELETE FROM detections WHERE detection_id = ?", (detection_id,)
        )
        conn.commit()
    finally:
        conn.close()
