# Smart Campus Object Monitoring System

A sensing, detection, and reporting platform for university campus environments.

**DSC 333 Final Project - Spring 2026**

---

## Architecture

- Raspberry Pi camera captures images and sends them to the backend over HTTP.
- The FastAPI backend stores metadata in SQLite, uploads files to Cloud Storage when configured, and calls Cloud Vision when credentials are available.
- The Streamlit dashboard reads from the backend API and shows recent detections, filters, and summary charts.

## Quick Start

Use Python 3.11 for local setup. That matches the Docker images in this repo and avoids package compatibility issues with newer Python releases.

### 1. Clone and set up

```bash
cd smart-campus-monitor

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env if you want to enable Google Cloud Storage and Vision locally

# Seed with sample data (for local development)
python seed.py
```

### 2. Start the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 3. Start the dashboard

```bash
cd dashboard
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

Open http://localhost:8501

### 4. (Optional) Raspberry Pi capture

```bash
# On the Pi
cd raspberry_pi
pip install -r requirements.txt
python capture.py --backend http://YOUR_SERVER:8000 --device-id 1 --interval 60
```

## Docker (alternative)

```bash
docker compose up --build
```

- Backend: http://localhost:8000
- Dashboard: http://localhost:8501

## GCP Setup

Cloud services are optional for local development. If you skip this section, uploads are stored locally on disk and detection is skipped.

1. **Create a project** in [Google Cloud Console](https://console.cloud.google.com)

2. **Enable APIs:**
   - Cloud Vision API
   - Cloud Storage

3. **Service account:**
   - Create a service account with roles: `Storage Object Admin`, `Vision API User`
   - Download the JSON key file
   - Set `GOOGLE_APPLICATION_CREDENTIALS=path/to/key.json` in `.env`

4. **Storage bucket:**
   - Create a Cloud Storage bucket
   - Set the bucket name in `.env` as `GOOGLE_CLOUD_STORAGE_BUCKET`

## Database Schema

### `devices`
| Column | Type | Notes |
|--------|------|-------|
| device_id | INTEGER | PK, auto-increment |
| device_name | TEXT | NOT NULL |
| location | TEXT | |
| status | TEXT | 'active' or 'inactive' |
| registered_at | TEXT | timestamp |

### `images`
| Column | Type | Notes |
|--------|------|-------|
| image_id | INTEGER | PK, auto-increment |
| device_id | INTEGER | FK -> devices |
| image_url | TEXT | GCS public URL |
| file_name | TEXT | |
| captured_at | TEXT | timestamp |

### `detections`
| Column | Type | Notes |
|--------|------|-------|
| detection_id | INTEGER | PK, auto-increment |
| image_id | INTEGER | FK -> images |
| device_id | INTEGER | FK -> devices |
| object_label | TEXT | Vision API label |
| confidence | REAL | 0.0 - 1.0 |
| detected_at | TEXT | timestamp |

### Relationships
- **One device -> many images** (`device_id`)
- **One image -> many detections** (`image_id`)
- **One device -> many detections** through images

## API Endpoints

### Devices
| Method | Path | Description |
|--------|------|-------------|
| POST | /devices | Register a new device |
| GET | /devices | List all devices |
| GET | /devices/{id} | Get device details |
| PUT | /devices/{id} | Update device info |
| DELETE | /devices/{id} | Remove device |

### Detections
| Method | Path | Description |
|--------|------|-------------|
| POST | /detections | Create detection record |
| GET | /detections | List detections (filterable) |
| GET | /detections/{id} | Get detection details |
| PUT | /detections/{id} | Update detection |
| DELETE | /detections/{id} | Delete detection |

### Images
| Method | Path | Description |
|--------|------|-------------|
| POST | /images/upload | Upload image + auto-detect |
| GET | /images | List images |
| GET | /images/{id} | Get image metadata |
| DELETE | /images/{id} | Delete image + GCS file |

### Reports
| Method | Path | Description |
|--------|------|-------------|
| GET | /reports/summary | Aggregated stats (JOIN queries) |
| GET | /reports/detections-over-time | Hourly counts for charts |
| GET | /reports/top-objects | Most detected objects |
| GET | /reports/recent-images-with-detections | Recent captures with counts |

## Project Structure

```text
smart-campus-monitor/
|-- backend/
|   |-- main.py
|   |-- config.py
|   |-- database.py
|   |-- models.py
|   |-- seed.py
|   |-- routers/
|   |   |-- devices.py
|   |   |-- detections.py
|   |   |-- images.py
|   |   `-- reports.py
|   |-- services/
|   |   |-- vision.py
|   |   `-- storage.py
|   |-- requirements.txt
|   `-- .env.example
|-- dashboard/
|   |-- app.py
|   `-- requirements.txt
|-- raspberry_pi/
|   |-- capture.py
|   `-- requirements.txt
|-- Dockerfile.backend
|-- Dockerfile.dashboard
|-- docker-compose.yml
`-- README.md
```

## Team Responsibilities

### Team Member A
- Raspberry Pi setup and camera configuration
- Image capture script development
- Cloud Storage upload integration
- End-to-end pipeline testing

### Team Member B
- FastAPI backend development
- Vision API integration and response parsing
- SQLite database design and schema creation
- JOIN query development and testing
- Streamlit dashboard development
- Filter and visualization implementation
