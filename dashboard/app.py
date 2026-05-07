"""
Streamlit Dashboard - Smart Campus Object Monitoring System

Displays recent detections, device info, and analytics
powered by the FastAPI backend.
"""
import os
from datetime import datetime

import plotly.express as px
import requests
import streamlit as st
import streamlit.components.v1 as components

# Config
st.set_page_config(
    page_title="Smart Campus Monitor",
    layout="wide",
    initial_sidebar_state="expanded",
)


def get_api_base() -> str:
    env_api_base = os.environ.get("API_BASE")
    if env_api_base:
        return env_api_base

    try:
        return st.secrets.get("API_BASE", "http://localhost:8000")
    except Exception:
        return "http://localhost:8000"


API_BASE = get_api_base()


# Helpers
def format_timestamp(value: str) -> str:
    """Format API timestamps for display."""
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value


def format_detection_rows(detections: list[dict]) -> list[dict]:
    """Format detection rows for Streamlit tables without pandas."""
    rows = []
    for item in detections:
        rows.append(
            {
                "object_label": item["object_label"],
                "confidence": f"{item['confidence']:.1%}",
                "detected_at": format_timestamp(item["detected_at"]),
                "device_name": item["device_name"],
                "location": item["location"],
            }
        )
    return rows


def format_device_rows(devices: list[dict]) -> list[dict]:
    """Format device rows for Streamlit tables without pandas."""
    rows = []
    for item in devices:
        row = dict(item)
        row["registered_at"] = format_timestamp(item["registered_at"])
        rows.append(row)
    return rows


def format_object_summary(detection: dict | None) -> str:
    """Return a compact label summary for the latest detection."""
    if not detection:
        return "No detections yet"
    return f"{detection['object_label']} ({detection['confidence']:.0%})"


def api_get(path: str, params: dict = None) -> dict | list | None:
    """GET request to the FastAPI backend."""
    try:
        resp = requests.get(f"{API_BASE}{path}", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"API error: {e}")
        return None


def api_post(path: str, json_data: dict = None, files: dict = None) -> dict | None:
    """POST request to the FastAPI backend."""
    try:
        if files:
            resp = requests.post(
                f"{API_BASE}{path}",
                files=files,
                data={"device_id": json_data.get("device_id")},
                timeout=30,
            )
        else:
            resp = requests.post(f"{API_BASE}{path}", json=json_data, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        st.error(f"API error: {e}")
        return None


def api_delete(path: str) -> bool:
    try:
        resp = requests.delete(f"{API_BASE}{path}", timeout=10)
        return resp.status_code in (200, 204)
    except requests.RequestException:
        return False


# Sidebar
st.sidebar.title("Campus Monitor")
page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Devices", "Upload Image"],
    index=0,
)

st.sidebar.markdown("---")

# Pages

if page == "Dashboard":
    st.title("Dashboard")
    st.markdown("Real-time object detection overview from campus cameras.")

    control_col1, control_col2 = st.columns([1, 2])
    with control_col1:
        if st.button("Refresh Now", use_container_width=True):
            st.rerun()
    with control_col2:
        auto_refresh = st.checkbox("Auto-refresh every 30 seconds", value=True)
        if auto_refresh:
            components.html(
                """
                <script>
                setTimeout(function() {
                    window.parent.location.reload();
                }, 30000);
                </script>
                """,
                height=0,
            )

    latest_images = api_get("/images", {"limit": 1}) or []
    latest_detections = api_get("/detections", {"limit": 1}) or []
    latest_image = latest_images[0] if latest_images else None
    latest_detection = latest_detections[0] if latest_detections else None

    spotlight_col, preview_col = st.columns([1.1, 0.9])
    with spotlight_col:
        st.subheader("Live Snapshot")
        snap_col1, snap_col2, snap_col3 = st.columns(3)
        snap_col1.metric(
            "Last Capture Time",
            format_timestamp(latest_image["captured_at"]) if latest_image else "No captures yet",
        )
        snap_col2.metric(
            "Last Detected Object",
            format_object_summary(latest_detection),
        )
        snap_col3.metric(
            "Preview Source",
            latest_detection["device_name"] if latest_detection else (
                f"Device {latest_image['device_id']}" if latest_image else "Waiting for data"
            ),
        )
        if latest_detection:
            st.caption(
                f"Latest detection came from {latest_detection['device_name']}"
                f" at {format_timestamp(latest_detection['detected_at'])}."
            )
        else:
            st.info(
                "No detections have been recorded yet. Keep the Pi capture loop running "
                "or upload an image from the Upload Image tab."
            )

    with preview_col:
        st.subheader("Latest Image")
        if latest_image:
            st.image(
                f"{API_BASE}/images/{latest_image['image_id']}/content",
                caption=f"Image {latest_image['image_id']} · {format_timestamp(latest_image['captured_at'])}",
                use_column_width=True,
            )
        else:
            st.info(
                "No images have been uploaded yet. Once the Pi sends a capture, the latest frame will appear here."
            )

    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    summary = api_get("/reports/summary")
    if summary:
        col1.metric("Total Detections", summary["total_detections"])
        col2.metric("Total Images", summary["total_images"])
        col3.metric("Active Devices", summary["total_devices"])
        col4.metric("Object Types", summary["unique_object_types"])

    st.markdown("---")

    # Filters
    with st.expander("Filters", expanded=False):
        filter_cols = st.columns(4)
        with filter_cols[0]:
            # Fetch unique labels for dropdown
            top_objects = api_get("/reports/top-objects", {"limit": 50})
            label_options = ["All"] + ([o["object_label"] for o in top_objects] if top_objects else [])
            selected_label = st.selectbox("Object Type", label_options)
        with filter_cols[1]:
            min_conf = st.slider("Min Confidence", 0.0, 1.0, 0.5, 0.05)
        with filter_cols[2]:
            time_options = {"Last hour": 1, "Last 6 hours": 6, "Last 24 hours": 24, "Last 7 days": 168}
            selected_time = st.selectbox("Time Range", list(time_options.keys()))
        with filter_cols[3]:
            devices = api_get("/devices")
            device_options = ["All"] + ([f"{d['device_id']}: {d['device_name']}" for d in devices] if devices else [])
            selected_device = st.selectbox("Device", device_options)

    # Build query params
    params = {"min_confidence": min_conf, "limit": 200}
    if selected_label != "All":
        params["object_label"] = selected_label
    params["hours"] = time_options[selected_time]
    if selected_device != "All":
        params["device_id"] = int(selected_device.split(":")[0])

    # Detection table
    st.subheader("Recent Detections")
    detections = api_get("/detections", params)
    if detections:
        st.dataframe(
            format_detection_rows(detections),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info(
            "No detections match these filters yet. Try widening the time range, lowering the confidence threshold, "
            "or waiting for the next camera upload."
        )

    st.markdown("---")

    # Charts
    chart_cols = st.columns(2)

    with chart_cols[0]:
        st.subheader("Detections Over Time")
        time_data = api_get("/reports/detections-over-time", {"hours": time_options[selected_time]})
        if time_data and len(time_data) > 0:
            fig = px.bar(
                x=[item["hour"] for item in time_data],
                y=[item["count"] for item in time_data],
                labels={"x": "Hour", "y": "Detections"},
            )
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No detection timeline yet. New uploads will start filling this chart automatically.")

    with chart_cols[1]:
        st.subheader("Top Detected Objects")
        if top_objects and len(top_objects) > 0:
            fig = px.pie(
                values=[item["count"] for item in top_objects],
                names=[item["object_label"] for item in top_objects],
                hole=0.4,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No detected labels yet. Once Vision returns results, the most common objects will appear here.")

    # Device activity
    if summary and summary.get("by_device"):
        st.markdown("---")
        st.subheader("Activity by Device")
        st.dataframe(summary["by_device"], use_container_width=True, hide_index=True)
    else:
        st.markdown("---")
        st.subheader("Activity by Device")
        st.info("No device activity has been recorded yet. Active devices will appear here after their first upload.")

elif page == "Devices":
    st.title("Device Management")

    devices = api_get("/devices")
    if devices:
        st.dataframe(format_device_rows(devices), use_container_width=True, hide_index=True)
    else:
        st.info("No devices are registered yet. Add your Raspberry Pi camera here before trying uploads.")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Register New Device")
        with st.form("new_device"):
            name = st.text_input("Device Name", placeholder="e.g., Lab 201 Camera")
            location = st.text_input("Location", placeholder="e.g., Science Building Room 201")
            submitted = st.form_submit_button("Register")
            if submitted and name:
                result = api_post("/devices/", {"device_name": name, "location": location})
                if result:
                    st.success(f"Device '{result['device_name']}' registered (ID: {result['device_id']})")
                    st.rerun()

    with col2:
        st.subheader("Update Device Status")
        if devices:
            dev_opts = {f"{d['device_id']}: {d['device_name']}": d["device_id"] for d in devices}
            selected = st.selectbox("Select Device", list(dev_opts.keys()))
            new_status = st.selectbox("New Status", ["active", "inactive"])
            if st.button("Update Status"):
                dev_id = dev_opts[selected]
                try:
                    resp = requests.put(f"{API_BASE}/devices/{dev_id}", json={"status": new_status}, timeout=10)
                    if resp.ok:
                        st.success("Status updated.")
                        st.rerun()
                    else:
                        st.error(f"Update failed: {resp.text}")
                except Exception as e:
                    st.error(str(e))

elif page == "Upload Image":
    st.title("Upload & Detect")
    st.markdown("Upload an image to trigger object detection via the Google Cloud Vision API.")

    devices = api_get("/devices")
    if not devices:
        st.warning("No devices are registered yet. Go to the Devices tab first, then come back here to upload.")
        st.stop()

    dev_opts = {f"{d['device_id']}: {d['device_name']} ({d['location'] or 'No location'})": d["device_id"] for d in devices}
    selected_dev = st.selectbox("Select Device", list(dev_opts.keys()))
    device_id = dev_opts[selected_dev]

    uploaded = st.file_uploader("Choose an image", type=["jpg", "jpeg", "png", "webp"])
    if uploaded:
        st.image(uploaded, caption="Preview", width=400)
        if st.button("Upload and Detect", type="primary"):
            with st.spinner("Uploading to cloud and running detection..."):
                result = api_post(
                    "/images/upload",
                    json_data={"device_id": device_id},
                    files={"file": (uploaded.name, uploaded, uploaded.type)},
                )
            if result:
                st.success(f"Image uploaded (ID: {result['image_id']})")
                st.json(result)
    else:
        st.info("Choose a device and image file to test the upload flow manually.")
