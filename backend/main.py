"""
Smart Campus Object Monitoring System
FastAPI Backend - Main Application

Endpoints:
  /devices          - CRUD for registered devices
  /detections       - CRUD for object detection records
  /images           - Upload, list, delete images (+ auto-detect)
  /reports          - Aggregated analytics and summaries
  /docs             - Auto-generated Swagger UI
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db
from routers import devices, detections, images, reports

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "A sensing, detection, and reporting platform "
        "for university campus environments."
    ),
    version="1.0.0",
)

# CORS - allow Streamlit dashboard and other clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(devices.router)
app.include_router(detections.router)
app.include_router(images.router)
app.include_router(reports.router)


@app.on_event("startup")
def startup():
    """Initialize database tables on startup."""
    init_db()
    logging.getLogger(__name__).info("Database initialized.")


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "ok", "service": settings.APP_NAME}


@app.get("/ping", tags=["Health"])
def ping():
    return {"pong": True}
