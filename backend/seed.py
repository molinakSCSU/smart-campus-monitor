"""
Seed script - creates sample devices and detections for local development.
Run:  python seed.py
"""
import random
from datetime import datetime, timedelta

from database import get_connection, init_db

LABELS = [
    "person", "laptop", "backpack", "chair", "phone",
    "book", "desk", "monitor", "keyboard", "mouse",
    "bottle", "cup", "whiteboard", "projector", "pen",
]

LOCATIONS = [
    "Science Building Room 201",
    "Engineering Lab 105",
    "Library Study Room 3B",
    "Student Union Lounge",
    "Computer Lab A",
]


def seed():
    init_db()
    conn = get_connection()

    # Create 4 devices
    devices = []
    for i, loc in enumerate(LOCATIONS[:4]):
        cur = conn.execute(
            "INSERT INTO devices (device_name, location) VALUES (?, ?)",
            (f"Camera-{i+1:02d}", loc),
        )
        conn.commit()
        devices.append(cur.lastrowid)
        print(f"  Created device: Camera-{i+1:02d} -> {loc}")

    # Create 200 images across devices
    now = datetime.now()
    for _ in range(200):
        device_id = random.choice(devices)
        hours_ago = random.uniform(0, 168)  # up to 7 days ago
        captured_at = (now - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S")
        image_url = f"https://storage.googleapis.com/mock-bucket/{device_id}/{captured_at[:10]}/img_{random.randint(1000,9999)}.jpg"

        cur = conn.execute(
            "INSERT INTO images (device_id, image_url, captured_at) VALUES (?, ?, ?)",
            (device_id, image_url, captured_at),
        )
        image_id = cur.lastrowid

        # 1-6 detections per image
        num_detections = random.randint(1, 6)
        labels = random.sample(LABELS, num_detections)
        for label in labels:
            confidence = round(random.uniform(0.55, 0.99), 3)
            conn.execute(
                "INSERT INTO detections (image_id, device_id, object_label, confidence, detected_at) VALUES (?, ?, ?, ?, ?)",
                (image_id, device_id, label, confidence, captured_at),
            )

    conn.commit()

    # Stats
    total_det = conn.execute("SELECT COUNT(*) FROM detections").fetchone()[0]
    total_img = conn.execute("SELECT COUNT(*) FROM images").fetchone()[0]
    print(f"\n  Seeded {len(devices)} devices, {total_img} images, {total_det} detections")
    conn.close()


if __name__ == "__main__":
    print("Seeding database...")
    seed()
