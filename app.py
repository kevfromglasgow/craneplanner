import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

# --- CONFIGURATION ---
st.set_page_config(page_title="LTM 1150-5.3 Pro Planner", layout="wide")

# Technical Data from Liebherr LTM 1150-5.3 Specs
# Max single line pull is 91.6 kN, which is approximately 9.34 metric tons 
MAX_LINE_PULL = 9.34  

HOOK_BLOCKS = {
    "116.9t (7-sheave)": {"weight": 1.240, "max_lines": 14}, # [cite: 107]
    "86.0t (5-sheave)": {"weight": 0.950, "max_lines": 10},  # [cite: 107]
    "61.6t (3-sheave)": {"weight": 0.700, "max_lines": 7},   # [cite: 107]
    "27.2t (1-sheave)": {"weight": 0.450, "max_lines": 3},   # [cite: 107]
    "9.2t (Single line)": {"weight": 0.350, "max_lines": 1}  # [cite: 107]
}

# --- CALCULATIONS ---
def get_rigging_math(load_w, sling_angle_deg, num_legs, gross_weight):
    angle_rad = math.radians(sling_angle_deg)
    # Vertical height of the sling triangle (Headroom consumed)
    rig_height = (load_w / 2) / math.tan(angle_rad) if sling_angle_deg > 0 else 0
    # Actual length of the sling legs
    sling_len = (load_w / 2) / math.sin(angle_rad) if sling_angle_deg > 0 else 0
    
    # Uniform Load Method Mode Factors
    if num_legs == 1: mode_f = 1.0
    elif num_legs == 2: mode_f = 2 * math.cos(angle_rad)
    else: mode_f = 2.1  # Standard for 3/4 legs
    
    tension_per_leg = (gross_weight / mode_f)
    return rig_height, sling_len, tension_per_leg

# --- SIDEBAR ---
st.sidebar.header("1. Load & Safety")
w_load = st.sidebar.number_input("Load Weight (t)", value=10.0)
load_w = st.sidebar.number_input("Load Width (m)", value=3.0)
load_h = st.sidebar.number_input("Load Height (m)", value=2.0)
fos = st.sidebar.slider("Factor of Safety", 1.0, 1.5, 1.2, step=0.05)
util_target = st.sidebar.slider("Target Utilisation (%)", 50, 100, 85)

st.sidebar.header("2. Rigging Setup")
num_legs = st.sidebar.selectbox("Number of Chain Legs", [1, 2, 3, 4])
sling_angle = st.sidebar.slider("Sling Angle from Vertical (°)", 10, 60, 30)
w_rigging = st.sidebar.number_input("Weight of Accessories/Rigging (t)", value=0.1)

st.sidebar.header("3. Crane & Hook Block")
hook_choice = st.sidebar.selectbox("Hook Block", list(HOOK_BLOCKS.keys()))
reeves = st.sidebar.number_input("Parts of Line (Reeves)", 1, HOOK_BLOCKS[hook_choice]['max_lines'], 2)

st.sidebar.header("4. Lift Geometry")
# Selectable boom lengths for LTM 1150-5.3 [cite: 903, 912]
boom_len = st.sidebar.select_slider(
    "Boom Length (m)", 
    options=[12.3, 16.4, 20.6, 24.7, 28.8, 32.9, 37.0, 41.1, 45.2, 49.4, 53.5, 57.6, 61.7, 66.0]
)
radius = st.sidebar.slider("Working Radius (m)", 3.0, float(boom_len) - 0.5, 15.0)

# --- EXECUTION LOGIC ---
w_hook = HOOK_BLOCKS[hook_choice]['weight']
total_gross = (w_load + w_hook + w_rigging) * fos
rig_v_height, s_actual_len, leg_tension = get_rigging_math(load_w, sling_angle, num_legs, total_gross)

# Line Pull Capacity Check - FIXED VARIABLE NAME HERE
line_capacity = reeves * MAX_LINE_PULL

# Boom Geometry
ratio = radius / boom_len
boom_angle_rad = math.acos(ratio)
tip_height = math.sin(boom_angle_rad) * boom_len

# Headroom Check (Tip Height - Hook Block ~2m - Rigging Triangle Height - Load Height)
headroom = tip_height - 2.0 - rig_v_height - load_h

# --- MAIN DASHBOARD ---
st.title("🏗️ LTM 1150-5.3 Professional Lift Planner")
st.markdown("---")

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("Gross Load (FOS)", f"{total_gross:.2f} t")
with c2:
    st.metric("Sling Length Required", f"{s_actual_len:.2f} m")
with c3:
    st.metric("Tension Per Leg", f"{leg_tension:.2f} t")
with c4:
    color = "normal" if headroom > 1.0 else "inverse"
    st.metric("Headroom Clearance", f"{headroom:.2f} m", delta_color=color)

# Visualization
fig = go.Figure()

# 1. THE CRANE STRUCTURE
fig.add_trace(go.Scatter(x=[-5, radius + 10], y=[0, 0], mode='lines', name='Ground', line=dict(color='green', width=2)))
fig.add_trace(go.Scatter(x=[0, radius], y=[2, tip_height], mode='lines+markers', name='Main Boom', line=dict(width=10, color='yellow')))

# 2. THE HANGING RIGGING
hook_y = tip_height - 2.0
rigging_base_y = hook_y - rig_v_height

fig.add_trace(go.Scatter(
    x=[radius - (load_w/2), radius, radius + (load_w/2)],
    y=[rigging_base_y, hook_y, rigging_base_y],
    fill='toself', name='Rigging Triangle', line=dict(color='orange', width=2)
))

# 3. THE LOAD BOX
fig.add_shape(type="rect", 
              x0=radius - (load_w/2), y0=rigging_base_y - load_h, 
              x1=radius + (load_w/2), y1=rigging_base_y, 
              fillcolor="rgba(128, 128, 128, 0.5)", line=dict(color="black"))

# Chart Formatting
fig.update_layout(
    height=700, 
    yaxis=dict(scaleanchor="x", scaleratio=1, title="Height (m)"),
    xaxis=dict(title="Radius (m)"),
    title="Side Elevation: Hanging Rigging & Load Verification"
)
st.plotly_chart(fig, use_container_width=True)

# --- SAFETY & COMPLIANCE LOG ---
st.subheader("Safety Compliance Check")
col_log1, col_log2 = st.columns(2)

with col_log1:
    if total_gross > line_capacity:
        st.error(f"❌ REEVING ERROR: Load ({total_gross:.2f}t) exceeds rope capacity ({line_capacity:.2f}t). Use more reeves.")
    else:
        st.success(f"✅ Rope Capacity: {reeves} reeves support up to {line_capacity:.2f}t.")

with col_log2:
    if headroom < 0.5:
        st.error(f"❌ HEADROOM CRITICAL: Only {headroom:.2f}m remaining. Shorten slings or increase boom length.")
    else:
        st.success(f"✅ Headroom Clearance is sufficient ({headroom:.2f}m).")

st.info(f"**Engineering Note:** This tool applies the Uniform Load Method for accessory WLL. For rigid loads on 4-legs, ensure equalizing equipment is used or derate to 2-leg capacity.")
