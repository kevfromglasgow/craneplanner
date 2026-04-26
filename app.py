import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

# --- CONFIGURATION ---
st.set_page_config(page_title="LTM 1150-5.3 Pro Planner", layout="wide")

# Technical Data from Liebherr LTM 1150-5.3 Technical Specifications
# Max single line pull is 91.6 kN
MAX_LINE_PULL = 9.34  

# Hook block weights and reeving limits
HOOK_BLOCKS = {
    "116.9t (7-sheave)": {"weight": 1.240, "max_lines": 14, "length": 1.5}, 
    "86.0t (5-sheave)": {"weight": 0.950, "max_lines": 10, "length": 1.2},  
    "61.6t (3-sheave)": {"weight": 0.700, "max_lines": 7, "length": 1.0},   
    "27.2t (1-sheave)": {"weight": 0.450, "max_lines": 3, "length": 0.8},   
    "9.2t (Single line)": {"weight": 0.350, "max_lines": 1, "length": 0.6}  
}

# --- CALCULATIONS ---
def get_rigging_math(load_w, sling_angle_deg, num_legs, gross_weight):
    """Calculates rigging heights and tensions using the Uniform Load Method."""
    angle_rad = math.radians(sling_angle_deg)
    # Vertical height of the sling triangle
    rig_v_height = (load_w / 2) / math.tan(angle_rad) if sling_angle_deg > 0 else 0
    # Actual length of the sling legs
    sling_len = (load_w / 2) / math.sin(angle_rad) if sling_angle_deg > 0 else 0
    
    # Mode Factors (Uniform Load Method)
    if num_legs == 1: 
        mode_f = 1.0
    elif num_legs == 2: 
        mode_f = 2 * math.cos(angle_rad)
    else: 
        # Standard factor for 3 and 4 leg slings is 2.1 to account for uneven loading
        mode_f = 2.1  
    
    min_wll_per_leg = (gross_weight / mode_f)
    return rig_v_height, sling_len, min_wll_per_leg

# --- SIDEBAR: INPUTS ---
st.sidebar.header("1. Load & Safety")
w_load = st.sidebar.number_input("Weight of Load (t)", value=10.0)
load_w = st.sidebar.number_input("Width of Load (m)", value=3.0)
load_h = st.sidebar.number_input("Height of Load (m)", value=2.0)
fos = st.sidebar.slider("Factor of Safety (FOS)", 1.0, 1.5, 1.2, step=0.05)

st.sidebar.header("2. Rigging Setup")
num_legs = st.sidebar.selectbox("Number of Sling Legs", [1, 2, 3, 4])
sling_angle = st.sidebar.slider("Sling Angle from Vertical (°)", 10, 60, 30)
w_rigging = st.sidebar.number_input("Weight of Accessories/Rigging (t)", value=0.1)
# Vertical gap between hook and master link/apex
master_link_gap = st.sidebar.slider("Hook to Sling Apex Gap (m)", 0.2, 2.0, 0.5)

st.sidebar.header("3. Crane Configuration")
hook_choice = st.sidebar.selectbox("Hook Block", list(HOOK_BLOCKS.keys()))
reeves = st.sidebar.number_input("Parts of Line (Reeves)", 1, HOOK_BLOCKS[hook_choice]['max_lines'], 2)
# Official telescopic boom steps
boom_len = st.sidebar.select_slider(
    "Boom Length (m)", 
    options=[12.3, 16.4, 20.6, 24.7, 28.8, 32.9, 37.0, 41.1, 45.2, 49.4, 53.5, 57.6, 61.7, 66.0]
)
# Radius cannot exceed boom length
radius = st.sidebar.slider("Working Radius (m)", 3.0, float(boom_len) - 1.0, 15.0)

# --- EXECUTION LOGIC ---
w_hook = HOOK_BLOCKS[hook_choice]['weight']
block_len = HOOK_BLOCKS[hook_choice]['length']
total_gross = (w_load + w_hook + w_rigging) * fos
rig_v_height, s_actual_len, leg_tension = get_rigging_math(load_w, sling_angle, num_legs, total_gross)

# Line Pull Capacity
line_capacity = reeves * MAX_LINE_PULL

# Boom Geometry
ratio = radius / boom_len
boom_angle_rad = math.acos(ratio)
tip_height = math.sin(boom_angle_rad) * boom_len

# Vertical Positions
apex_y = tip_height - block_len - master_link_gap
rigging_base_y = apex_y - rig_v_height
headroom = rigging_base_y - load_h

# BOOM INTERFERENCE (Foul Check)
# Check horizontal clearance at the load's shoulder height
dist_to_boom_face = rigging_base_y / math.tan(boom_angle_rad)
# Gap = (Radius - Distance to face) - (Half width of load)
foul_gap = (radius - dist_to_boom_face) - (load_w / 2)

# --- MAIN UI ---
st.title("🏗️ LTM 1150-5.3 Pro Planner: Collision & Headroom")
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
fig.add_trace(go.Scatter(x=[-2, radius + 10], y=[0, 0], mode='lines', name='Ground', line=dict(color='green', width=2)))
fig.add_trace(go.Scatter(x=[0, radius], y=[2.3, tip_height], mode='lines+markers', name='Main Boom', line=dict(width=12, color='yellow')))

# 2. ROPE & MASTER LINK GAP
fig.add_trace(go.Scatter(
    x=[radius, radius], 
    y=[tip_height - block_len, apex_y], 
    mode='lines', name='Master Link Gap', line=dict(color='black', dash='dot', width=2)
))

# 3. THE HANGING RIGGING
fig.add_trace(go.Scatter(
    x=[radius - (load_w/2), radius, radius + (load_w/2)],
    y=[rigging_base_y, apex_y, rigging_base_y],
    fill='toself', name='Rigging Triangle', line=dict(color='orange', width=2)
))

# 4. THE LOAD BOX
fig.add_shape(type="rect", 
              x0=radius - (load_w/2), y0=rigging_base_y - load_h, 
              x1=radius + (load_w/2), y1=rigging_base_y, 
              fillcolor="rgba(128, 128, 128, 0.5)", line=dict(color="black"))

# Chart Formatting
fig.update_layout(
    height=700, 
    yaxis=dict(scaleanchor="x", scaleratio=1, title="Height (m)"),
    xaxis=dict(title="Radius (m)"),
    title="Lift Profile & Foul Analysis"
)
st.plotly_chart(fig, use_container_width=True)

# --- SAFETY CHECKS ---
st.subheader("Safety Compliance Log")
col_log1, col_log2, col_log3 = st.columns(3)

with col_log1:
    if total_gross > line_capacity:
        st.error(f"❌ REEVING: Load ({total_gross:.2f}t) exceeds rope capacity ({line_capacity:.2f}t).")
    else:
        st.success(f"✅ Reeving: {reeves} lines support {line_capacity:.2f}t.")

with col_log2:
    if headroom < 0.5:
        st.error(f"❌ HEADROOM: Critical clearance ({headroom:.2f}m).")
    else:
        st.success(f"✅ Headroom OK ({headroom:.2f}m).")

with col_log3:
    if foul_gap < 0.3:
        st.error(f"❌ BOOM INTERFERENCE: Load is only {foul_gap:.2f}m from boom face!")
    else:
        st.success(f"✅ Boom Clearance OK ({foul_gap:.2f}m).")
