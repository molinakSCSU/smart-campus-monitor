import sqlite3
from pathlib import Path

from config import settings

DB_PATH = Path(settings.DATABASE_PATH)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create all tables if they don't exist."""
    conn = get_connection()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS devices (
    device_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    device_name     TEXT    NOT NULL,
    location        TEXT,
    status          TEXT    DEFAULT 'active',
    registered_at   TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS images (
    image_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id       INTEGER NOT NULL,
    image_url       TEXT    NOT NULL,
    file_name       TEXT,
    captured_at     TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS detections (
    detection_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id        INTEGER NOT NULL,
    device_id       INTEGER NOT NULL,
    object_label    TEXT    NOT NULL,
    confidence      REAL    NOT NULL,
    detected_at     TEXT    DEFAULT (datetime('now')),
    FOREIGN KEY (image_id)  REFERENCES images(image_id)   ON DELETE CASCADE,
    FOREIGN KEY (device_id) REFERENCES devices(device_id)  ON DELETE CASCADE
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_images_device ON images(device_id, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_detections_image ON detections(image_id);
CREATE INDEX IF NOT EXISTS idx_detections_device ON detections(device_id, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_detections_label ON detections(object_label, detected_at DESC);
CREATE INDEX IF NOT EXISTS idx_detections_confidence ON detections(confidence);
"""
