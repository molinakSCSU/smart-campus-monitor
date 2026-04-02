"""Report and analytics endpoints using JOIN queries."""
import logging
from typing import Optional

from fastapi import APIRouter, Query

from database import get_connection
from models import DetectionCountByDevice, DetectionCountByLabel, ReportSummary

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/summary", response_model=ReportSummary)
def get_summary():
    """
    Aggregated detection counts by object type and device.
    Uses JOIN queries across all three tables.
    """
    conn = get_connection()
    try:
        # Totals
        totals = conn.execute("""
            SELECT
                (SELECT COUNT(*) FROM detections) AS total_detections,
                (SELECT COUNT(*) FROM images) AS total_images,
                (SELECT COUNT(*) FROM devices WHERE status = 'active') AS total_devices,
                (SELECT COUNT(DISTINCT object_label) FROM detections) AS unique_object_types
        """).fetchone()

        # By device (JOIN detections + devices)
        device_rows = conn.execute("""
            SELECT dev.device_name, dev.location,
                   COUNT(d.detection_id) AS total_detections
            FROM detections d
            JOIN devices dev ON d.device_id = dev.device_id
            GROUP BY dev.device_id
            ORDER BY total_detections DESC
        """).fetchall()

        # By label
        label_rows = conn.execute("""
            SELECT object_label,
                   COUNT(*) AS total_detections,
                   ROUND(AVG(confidence), 3) AS avg_confidence
            FROM detections
            GROUP BY object_label
            ORDER BY total_detections DESC
        """).fetchall()

        return ReportSummary(
            total_detections=totals["total_detections"],
            total_images=totals["total_images"],
            total_devices=totals["total_devices"],
            unique_object_types=totals["unique_object_types"],
            by_device=[
                DetectionCountByDevice(**dict(r)) for r in device_rows
            ],
            by_label=[
                DetectionCountByLabel(**dict(r)) for r in label_rows
            ],
        )
    finally:
        conn.close()


@router.get("/detections-over-time")
def detections_over_time(
    hours: int = Query(24, ge=1, le=720),
    device_id: Optional[int] = None,
):
    """Detection counts grouped by hour for time-series charting."""
    conn = get_connection()
    try:
        query = """
            SELECT
                strftime('%Y-%m-%d %H:00', detected_at) AS hour,
                COUNT(*) AS count
            FROM detections
            WHERE detected_at >= datetime('now', ?)
        """
        params: list = [f"-{hours} hours"]

        if device_id:
            query += " AND device_id = ?"
            params.append(device_id)

        query += " GROUP BY hour ORDER BY hour"

        rows = conn.execute(query, params).fetchall()
        return [{"hour": r["hour"], "count": r["count"]} for r in rows]
    finally:
        conn.close()


@router.get("/top-objects")
def top_objects(limit: int = Query(10, ge=1, le=50)):
    """Most frequently detected objects."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT object_label,
                   COUNT(*) AS count,
                   ROUND(AVG(confidence), 3) AS avg_confidence
            FROM detections
            GROUP BY object_label
            ORDER BY count DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/recent-images-with-detections")
def recent_images_with_detections(limit: int = Query(20, ge=1, le=100)):
    """Recent images with detection counts (JOIN images + detections)."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT img.image_id, img.captured_at, img.image_url,
                   COUNT(d.detection_id) AS objects_found
            FROM images img
            LEFT JOIN detections d ON img.image_id = d.image_id
            GROUP BY img.image_id
            ORDER BY img.captured_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
