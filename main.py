import streamlit as st
import numpy as np

st.set_page_config(page_title="SmartTCD Dashboard", layout="wide")

st.title("🧠 SmartTCD: Real-Time Hemodynamic Monitoring")
st.markdown("---")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="Peak Systolic Velocity (PSV)", value="112.4 cm/s", delta="+3.2")
with col2:
    st.metric(label="Pulsatility Index (PI)", value="0.88", delta="-0.02")
with col3:
    st.metric(label="Mean Flow Velocity (MFV)", value="68.1 cm/s", delta="+1.1")

st.markdown("### 📈 Live Doppler Spectrogram / Waveform")
chart_data = st.line_chart(np.random.randn(50, 1) * 0.5 + 1.5)

if st.button("Refresh Stream"):
    new_data = np.random.randn(50, 1) * 0.5 + 1.5
    chart_data.add_rows(new_data)

