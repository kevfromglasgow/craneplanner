import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

# --- CONFIGURATION ---
st.set_page_config(page_title="LTM 1150-5.3 Rigging Workspace", layout="wide")

# Technical Data from Liebherr LTM 1150-5.3 Specs
MAX_LINE_PULL = 9.34  
HOOK_BLOCKS = {
    "116.9t (7-sheave)": {"weight": 1.240, "max_lines": 14, "length": 1.5}, 
    "86.0t (5-sheave)": {"weight": 0.950, "max_lines": 10, "length": 1.2},  
    "61.6t (3-sheave)": {"weight": 0.700, "max_lines": 7, "length": 1.0},   
    "27.2t (1-sheave)": {"weight": 0.450, "max_lines": 3, "length": 0.8},   
    "9.2t (Single line)": {"weight": 0.350, "max_lines": 1, "length": 0.6}  
}

# --- CALCULATIONS ---
def get_rigging_math(load_w, sling_angle_deg, num_legs, gross_weight):
    """Calculates rigging using the Uniform Load Method factors."""
    angle_rad = math.radians(sling_angle_deg)
    
    # 1. Geometry Math
    rig_v_height = (load_w / 2) / math.tan(angle_rad) if sling_angle_deg > 0 else 0
    sling_len = (load_w / 2) / math.sin(angle_rad) if sling_angle_deg > 0 else 0
    
    # 2. Mode Factor Logic (Uniform Load Method)
    mode_f = 1.0
    if num_legs == 2:
        mode_f = 1.4 if sling_angle_deg <= 45 else 1.0
    elif num_legs >= 3:
        mode_f = 2.1 if sling_angle_deg <= 45 else 1.5
    elif num_legs == 1:
        mode_f = 1.0
        
    # Min WLL required per leg
    min_wll_per_leg = gross_weight / mode_f
    return rig_v_height, sling_len, mode_f, min_wll_per_leg

# --- SIDEBAR: INPUTS ---
st.sidebar.header("1. Load & Safety")
w_load = st.sidebar.number_input("Weight of Load (t)", value=10.0)
load_w = st.sidebar.number_input("Width of Load (m)", value=3.0)
load_h = st.sidebar.number_input("Height of Load (m)", value=2.0)
fos = st.sidebar.slider("Factor of Safety", 1.0, 1.5, 1.2, step=0.05)

st.sidebar.header("2. Rigging Workspace")
# Primary toggle: Set by Height or Set by Angle
rig_method = st.sidebar.radio("Set Rigging By:", ["Vertical Height", "Sling Angle"])

if rig_method == "Vertical Height":
    rig_v_height_in = st.sidebar.slider("Set Vertical Height (m)", 0.5, 10.0, 2.5)
    # Calculate angle from height
    sling_angle = math.degrees(math.atan((load_w / 2) / rig_v_height_in))
else:
    sling_angle = st.sidebar.slider("Set Sling Angle from Vertical (°)", 10, 60, 30)

num_legs = st.sidebar.selectbox("Number of Sling Legs", [1, 2, 3, 4])
w_rigging = st.sidebar.number_input("Weight of Rigging (t)", value=0.1)
master_link_gap = st.sidebar.slider("Hook to Sling Apex Gap (m)", 0.2, 2.0, 0.5)

st.sidebar.header("3. Crane Setup")
hook_choice = st.sidebar.selectbox("Hook Block", list(HOOK_BLOCKS.keys()))
reeves = st.sidebar.number_input("Rope Reeves", 1, HOOK_BLOCKS[hook_choice]['max_lines'], 2)
boom_len = st.sidebar.select_slider("Boom Length (m)", options=[12.3, 16.4, 20.6, 24.7, 28.8, 32.9, 37.0, 41.1, 45.2, 49.4, 53.5, 57.6, 61.7, 66.0])
radius = st.sidebar.slider("Radius (m)", 3.0, float(boom_len) - 1.0, 15.0)

# --- EXECUTION ---
w_hook = HOOK_BLOCKS[hook_choice]['weight']
block_len = HOOK_BLOCKS[hook_choice]['length']
total_gross = (w_load + w_hook + w_rigging) * fos

# Calculate Rigging with Uniform Load Method
rig_v_height, s_actual_len, mode_f, min_wll_per_leg = get_rigging_math(load_w, sling_angle, num_legs, total_gross)

# Crane Geometry Logic
boom_angle = math.degrees(math.acos(radius / boom_len))
tip_h = math.sin(math.acos(radius / boom_len)) * boom_len
apex_y = tip_h - block_len - master_link_gap
rig_base_y = apex_y - rig_v_height
headroom_to_ground = rig_base_y - load_h

# Collision check
dist_to_boom = rig_base_y / math.tan(math.radians(boom_angle))
foul_gap = (radius - dist_to_boom) - (load_w / 2)

# --- DASHBOARD ---
st.title("🏗️ LTM 1150-5.3: Rigging Calculation Engine")

# Math panel
col_math, col_viz = st.columns([1, 2])

with col_math:
    st.subheader("📐 The Working (Rigging)")
    
    # Explain the mode factor band
    band = "0°-45°" if sling_angle <= 45 else "45°-60°"
    st.info(f"**Uniform Load Method:**\nUsing factor for {num_legs}-leg sling in the **{band}** band.")
    
    st.write(f"**Mode Factor ($M$):** {mode_f}")
    st.write(f"**Sling Leg Tension:** {total_gross/mode_f:.2f} t")
    st.markdown("---")
    st.write(f"**Geometry:**")
    st.write(f"Vertical Height ($H$): {rig_v_height:.2f} m")
    st.write(f"Sling Angle ($\alpha$): {sling_angle:.1f}°")
    st.write(f"Sling Length ($L$): {s_actual_len:.2f} m")
    
    st.subheader("🛠️ Accessory Specs")
    st.success(f"**Minimum WLL Required per leg:** {min_wll_per_leg:.2f} t")

with col_viz:
    fig = go.Figure()
    # Ground and Crane
    fig.add_trace(go.Scatter(x=[-2, radius+5], y=[0,0], mode='lines', line=dict(color='green'), name="Ground"))
    fig.add_trace(go.Scatter(x=[0, radius], y=[2.3, tip_h], mode='lines+markers', line=dict(width=10, color='yellow'), name="Boom"))
    
    # Rigging Triangle (Hanging from Apex)
    fig.add_trace(go.Scatter(
        x=[radius - (load_w/2), radius, radius + (load_w/2)],
        y=[rig_base_y, apex_y, rig_base_y],
        fill='toself', name='Sling Triangle', line=dict(color='orange')
    ))
    
    # Dimensions Overlay
    fig.add_annotation(x=radius, y=apex_y - (rig_v_height/2), text=f"H={rig_v_height:.2f}m", showarrow=True, arrowhead=1)
    fig.add_annotation(x=radius - (load_w/4), y=rig_base_y + (rig_v_height/2), text=f"L={s_actual_len:.2f}m", showarrow=False)
    
    # Load
    fig.add_shape(type="rect", x0=radius-(load_w/2), y0=rig_base_y-load_h, x1=radius+(load_w/2), y1=rig_base_y, fillcolor="rgba(128,128,128,0.5)")

    fig.update_layout(height=650, yaxis=dict(scaleanchor="x", scaleratio=1), title="Geometry & Foul Verification")
    st.plotly_chart(fig, use_container_width=True)

# Safety Summary
st.subheader("Compliance Check")
sc1, sc2, sc3 = st.columns(3)
with sc1:
    if total_gross > (reeves * MAX_LINE_PULL): st.error("❌ Line Pull Exceeded")
    else: st.success(f"✅ Line Pull OK ({reeves * MAX_LINE_PULL:.1f}t)")
with sc2:
    if headroom_to_ground < 0.2: st.error("❌ Headroom Critical")
    else: st.success(f"✅ Headroom OK ({headroom_to_ground:.2f}m)")
with sc3:
    if foul_gap < 0.3: st.error("❌ Boom Interference")
    else: st.success(f"✅ Boom Clearance OK ({foul_gap:.2f}m)")
