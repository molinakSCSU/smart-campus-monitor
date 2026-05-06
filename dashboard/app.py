"""
Streamlit Dashboard - Smart Campus Object Monitoring System

Displays recent detections, device info, and analytics
powered by the FastAPI backend.
"""
import os

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

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
        df = pd.DataFrame(detections)
        df["detected_at"] = pd.to_datetime(df["detected_at"]).dt.strftime("%Y-%m-%d %H:%M")
        df["confidence"] = df["confidence"].apply(lambda x: f"{x:.1%}")
        df_display = df[["object_label", "confidence", "detected_at", "device_name", "location"]]
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("No detections found matching the current filters.")

    st.markdown("---")

    # Charts
    chart_cols = st.columns(2)

    with chart_cols[0]:
        st.subheader("Detections Over Time")
        time_data = api_get("/reports/detections-over-time", {"hours": time_options[selected_time]})
        if time_data and len(time_data) > 0:
            tdf = pd.DataFrame(time_data)
            fig = px.bar(tdf, x="hour", y="count", labels={"hour": "Hour", "count": "Detections"})
            fig.update_xaxes(tickangle=45)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No time-series data available.")

    with chart_cols[1]:
        st.subheader("Top Detected Objects")
        if top_objects and len(top_objects) > 0:
            odf = pd.DataFrame(top_objects)
            fig = px.pie(odf, values="count", names="object_label", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No object data available.")

    # Device activity
    if summary and summary.get("by_device"):
        st.markdown("---")
        st.subheader("Activity by Device")
        ddf = pd.DataFrame(summary["by_device"])
        st.dataframe(ddf, use_container_width=True, hide_index=True)

elif page == "Devices":
    st.title("Device Management")

    devices = api_get("/devices")
    if devices:
        df = pd.DataFrame(devices)
        df["registered_at"] = pd.to_datetime(df["registered_at"]).dt.strftime("%Y-%m-%d %H:%M")
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No devices registered yet.")

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
        st.warning("No devices registered. Please register a device first.")
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
