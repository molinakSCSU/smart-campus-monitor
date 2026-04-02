"""CRUD endpoints for devices."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from database import get_connection
from models import DeviceCreate, DeviceResponse, DeviceUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/devices", tags=["Devices"])


def _row_to_device(row) -> DeviceResponse:
    return DeviceResponse(**dict(row))


@router.post("/", response_model=DeviceResponse, status_code=201)
def create_device(body: DeviceCreate):
    """Register a new device."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO devices (device_name, location) VALUES (?, ?)",
            (body.device_name, body.location),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM devices WHERE device_id = ?", (cur.lastrowid,)
        ).fetchone()
        return _row_to_device(row)
    finally:
        conn.close()


@router.get("/", response_model=list[DeviceResponse])
def list_devices():
    """List all registered devices."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM devices ORDER BY registered_at DESC").fetchall()
        return [_row_to_device(r) for r in rows]
    finally:
        conn.close()


@router.get("/{device_id}", response_model=DeviceResponse)
def get_device(device_id: int):
    """Retrieve details for a specific device."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM devices WHERE device_id = ?", (device_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Device not found")
        return _row_to_device(row)
    finally:
        conn.close()


@router.put("/{device_id}", response_model=DeviceResponse)
def update_device(device_id: int, body: DeviceUpdate):
    """Update device info (location, status)."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM devices WHERE device_id = ?", (device_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Device not found")

        updates = []
        params = []
        if body.device_name is not None:
            updates.append("device_name = ?")
            params.append(body.device_name)
        if body.location is not None:
            updates.append("location = ?")
            params.append(body.location)
        if body.status is not None:
            updates.append("status = ?")
            params.append(body.status)

        if not updates:
            return _row_to_device(row)

        params.append(device_id)
        conn.execute(
            f"UPDATE devices SET {', '.join(updates)} WHERE device_id = ?",
            params,
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM devices WHERE device_id = ?", (device_id,)
        ).fetchone()
        return _row_to_device(row)
    finally:
        conn.close()


@router.delete("/{device_id}", status_code=204)
def delete_device(device_id: int):
    """Remove a device and associated records (cascade)."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM devices WHERE device_id = ?", (device_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Device not found")
        conn.execute("DELETE FROM devices WHERE device_id = ?", (device_id,))
        conn.commit()
    finally:
        conn.close()
