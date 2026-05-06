from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# Device schemas

class DeviceCreate(BaseModel):
    device_name: str = Field(..., min_length=1, max_length=100)
    location: Optional[str] = None


class DeviceUpdate(BaseModel):
    device_name: Optional[str] = Field(None, min_length=1, max_length=100)
    location: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(active|inactive)$")


class DeviceResponse(BaseModel):
    device_id: int
    device_name: str
    location: Optional[str]
    status: str
    registered_at: str


# Image schemas

class ImageResponse(BaseModel):
    image_id: int
    device_id: int
    image_url: str
    file_name: Optional[str]
    captured_at: str


# Detection schemas

class DetectionCreate(BaseModel):
    image_id: int
    device_id: int
    object_label: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)


class DetectionUpdate(BaseModel):
    object_label: Optional[str] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class DetectionResponse(BaseModel):
    detection_id: int
    image_id: int
    device_id: int
    object_label: str
    confidence: float
    detected_at: str


class DetectionDetail(BaseModel):
    """Detection enriched with device and image info (JOIN result)."""
    detection_id: int
    object_label: str
    confidence: float
    detected_at: str
    device_name: str
    location: Optional[str]
    image_url: str


# Report schemas

class DetectionCountByDevice(BaseModel):
    device_name: str
    location: Optional[str]
    total_detections: int


class DetectionCountByLabel(BaseModel):
    object_label: str
    total_detections: int
    avg_confidence: float


class ReportSummary(BaseModel):
    total_detections: int
    total_images: int
    total_devices: int
    unique_object_types: int
    by_device: list[DetectionCountByDevice]
    by_label: list[DetectionCountByLabel]
