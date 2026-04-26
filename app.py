import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

# --- CONFIGURATION ---
st.set_page_config(page_title="Pro Crane Planner: LTM 1150-5.3", layout="wide")

# Technical Data from Liebherr LTM 1150-5.3 Specs
MAX_SINGLE_LINE_PULL = 9.34  # 91.6 kN converted to metric tons 
HOOK_BLOCK_DATA = {
    "116.9t (7-sheave)": {"weight": 1.240, "max_lines": 14}, # [cite: 107]
    "86.0t (5-sheave)": {"weight": 0.950, "max_lines": 10},  # [cite: 107]
    "61.6t (3-sheave)": {"weight": 0.700, "max_lines": 7},   # [cite: 107]
    "27.2t (1-sheave)": {"weight": 0.450, "max_lines": 3},   # [cite: 107]
    "9.2t (Single line)": {"weight": 0.350, "max_lines": 1}  # [cite: 107]
}

# --- CALCULATIONS ---
def get_rigging_geometry(load_w, load_h, sling_angle_deg, num_legs):
    # Trig to find min sling length to reach corners
    # Half width of load is the adjacent side if lifting from center
    angle_rad = math.radians(sling_angle_deg)
    if sling_angle_deg == 0:
        return 0, load_h
    
    min_sling_len = (load_w / 2) / math.sin(angle_rad)
    rigging_height = (load_w / 2) / math.tan(angle_rad)
    
    # Mode Factors (Uniform Load Method)
    if num_legs == 1: mode_factor = 1.0
    elif num_legs == 2: mode_factor = 2 * math.cos(angle_rad)
    else: mode_factor = 2.1 # Standard for 3/4 legs
    
    return min_sling_len, rigging_height, mode_factor

# --- SIDEBAR ---
st.sidebar.header("1. Load Dimensions & Weight")
w_load_net = st.sidebar.number_input("Weight of Load (t)", value=10.0)
load_w = st.sidebar.number_input("Load Width/Spread (m)", value=2.0)
load_h = st.sidebar.number_input("Load Height (m)", value=2.0)
fos = st.sidebar.slider("Factor of Safety", 1.0, 1.5, 1.2)

st.sidebar.header("2. Crane Setup")
counterweight = st.sidebar.selectbox("Counterweight (t)", [45, 29, 12, 6.2]) # [cite: 165, 434, 448]
hook_choice = st.sidebar.selectbox("Hook Block", list(HOOK_BLOCK_DATA.keys()))
reeves = st.sidebar.number_input("Number of Rope Reeves", min_value=1, max_value=HOOK_BLOCK_DATA[hook_choice]['max_lines'], value=2)

st.sidebar.header("3. Rigging Selection")
num_legs = st.sidebar.selectbox("Number of Chain Legs", [1, 2, 3, 4])
sling_angle = st.sidebar.slider("Sling Angle from Vertical (°)", 0, 60, 30)
w_accessories = st.sidebar.number_input("Weight of Accessories (t)", value=0.1)

st.sidebar.header("4. Lift Planning")
radius = st.sidebar.slider("Working Radius (m)", 3, 64, 20) # [cite: 964, 1143]
util_target = st.sidebar.slider("Max Utilisation (%)", 50, 100, 85)

# --- ENGINE ---
# Geometry Calculation
min_sling_len, rig_height, mode_f = get_rigging_geometry(load_w, load_h, sling_angle, num_legs)

# Total Weight Calculation
w_hook = HOOK_BLOCK_DATA[hook_choice]['weight']
total_gross_weight = (w_load_net + w_hook + w_accessories) * fos

# Line Pull Check
total_capacity_of_lines = reeves * MAX_SINGLE_LINE_PULL
min_wll_per_leg = total_gross_weight / mode_f

# --- VISUALIZATION ---
st.title("🏗️ LTM 1150-5.3 Pro Planner")

col1, col2, col3 = st.columns(3)
col1.metric("Gross Weight", f"{total_gross_weight:.2f} t")
col2.metric("Min. Sling Length", f"{min_sling_len:.2f} m")
col3.metric("Min. WLL / Leg", f"{min_wll_per_leg:.2f} t")

# Error Checking
if total_gross_weight > total_capacity_of_lines:
    st.error(f"❌ ROPE LIMIT EXCEEDED: {reeves} reeves only support {total_capacity_of_lines:.2f}t. Increase reeving.")

# Plotting the Trig & Lift
fig = go.Figure()

# 1. THE RIGGING TRIANGLE (Overlayed View)
# We center the triangle at the load center
tx = [-(load_w/2), 0, (load_w/2)]
ty = [0, rig_height, 0]
fig.add_trace(go.Scatter(x=tx, y=ty, fill='toself', name='Rigging Triangle', line=dict(color='orange')))
fig.add_annotation(x=0, y=rig_height/2, text=f"Angle: {sling_angle}°", showarrow=False)

# 2. THE CRANE GEOMETRY (Simplified)
# Assume boom length of 30m for visualization if data not loaded
boom_len = 35.0 
boom_angle = math.degrees(math.acos(radius/boom_len)) if radius < boom_len else 0
tip_h = math.sqrt(boom_len**2 - radius**2) if radius < boom_len else 0

# Draw Boom
fig.add_trace(go.Scatter(x=[-(radius+5), radius-radius], y=[0, 0], mode='lines', name='Ground', line=dict(color='green')))
fig.add_trace(go.Scatter(x=[0, radius], y=[2, tip_h], mode='lines+markers', name='Boom', line=dict(width=10, color='yellow')))

# 3. THE LOAD BOX
fig.add_shape(type="rect", x0=radius-(load_w/2), y0=0, x1=radius+(load_w/2), y1=load_h, line=dict(color="black"), fillcolor="gray")

# Final Figure Styling
fig.update_layout(
    title="Rigging Trig & Lift Geometry Overlay",
    xaxis_title="Horizontal Distance (m)",
    yaxis_title="Height (m)",
    height=700,
    showlegend=True,
    yaxis=dict(scaleanchor="x", scaleratio=1)
)

st.plotly_chart(fig, use_container_width=True)

# --- HEADROOM CALCULATION ---
# Total height from ground to hook
# Tip height - block height (approx 2m) - rigging height
headroom = tip_h - 2.0 - rig_height - load_h
st.subheader("Headroom & Deflection Analysis")
if headroom < 1.0:
    st.warning(f"⚠️ HEADROOM CRITICAL: {headroom:.2f}m available. Watch for boom deflection!")
else:
    st.success(f"Clear Headroom: {headroom:.2f}m")

st.info(f"Mechanical Check: Max Single Line Pull for LTM 1150-5.3 is {MAX_SINGLE_LINE_PULL} t per reeve.")
