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

# --- SIDEBAR: INPUTS ---
st.sidebar.header("1. Load & Safety")
w_load = st.sidebar.number_input("Weight of Load (t)", value=10.0)
load_w = st.sidebar.number_input("Width of Load (m)", value=3.0)
load_h = st.sidebar.number_input("Height of Load (m)", value=2.0)
fos = st.sidebar.slider("Factor of Safety", 1.0, 1.5, 1.2, step=0.05)

st.sidebar.header("2. Rigging Workspace")
# Primary toggle: Set by Height or Set by Angle
rig_method = st.sidebar.radio("Rigging Calculation Method", ["Set Vertical Height", "Set Sling Angle"])

if rig_method == "Set Vertical Height":
    rig_v_height = st.sidebar.slider("Vertical Height of Slings (m)", 0.5, 10.0, 2.5)
    # Solve for angle: tan(angle) = (w/2) / height
    sling_angle = math.degrees(math.atan((load_w / 2) / rig_v_height))
else:
    sling_angle = st.sidebar.slider("Sling Angle from Vertical (°)", 10, 60, 30)
    # Solve for height: height = (w/2) / tan(angle)
    rig_v_height = (load_w / 2) / math.tan(math.radians(sling_angle))

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

# Sling Trig
angle_rad = math.radians(sling_angle)
s_actual_len = (load_w / 2) / math.sin(angle_rad)

# Mode Factor
if num_legs == 1: mode_f = 1.0
elif num_legs == 2: mode_f = 2 * math.cos(angle_rad)
else: mode_f = 2.1 # Uniform Load Method

leg_tension = total_gross / mode_f

# Geometry
boom_angle = math.degrees(math.acos(radius / boom_len))
tip_h = math.sin(math.acos(radius / boom_len)) * boom_len
apex_y = tip_h - block_len - master_link_gap
rig_base_y = apex_y - rig_v_height
headroom = rig_base_y - load_h

# Foul Check
dist_to_boom = rig_base_y / math.tan(math.radians(boom_angle))
foul_gap = (radius - dist_to_boom) - (load_w / 2)

# --- UI DASHBOARD ---
st.title("🏗️ LTM 1150-5.3: Rigging Calculation Engine")

# Display the "Working" for the Rigging Triangle
col_math1, col_math2 = st.columns([1, 2])

with col_math1:
    st.subheader("📐 Rigging 'The Working'")
    st.markdown(f"""
    **Triangle Dimensions:**
    * **Vertical Height ($H$):** {rig_v_height:.2f} m
    * **Sling Angle ($\alpha$):** {sling_angle:.1f}°
    * **Sling Leg Length ($L$):** {s_actual_len:.2f} m
    * **Load Spread ($W$):** {load_w:.2f} m
    
    **Formula Used:**
    $L = \\frac{{W/2}}{{\\sin(\\alpha)}}$
    
    **Tension Check:**
    * **Mode Factor:** {mode_f:.2f}
    * **Tension/Leg:** {leg_tension:.2f} t
    """)
    
    if sling_angle > 45:
        st.error("⚠️ WARNING: Sling angle exceeds 45°. Significant tension increase per leg.")

with col_math2:
    # Visualization with explicit labels
    fig = go.Figure()
    # Ground
    fig.add_trace(go.Scatter(x=[-2, radius+5], y=[0,0], mode='lines', line=dict(color='green'), name="Ground"))
    # Boom
    fig.add_trace(go.Scatter(x=[0, radius], y=[2.3, tip_h], mode='lines+markers', line=dict(width=10, color='yellow'), name="Boom"))
    
    # Rigging Triangle
    fig.add_trace(go.Scatter(
        x=[radius - (load_w/2), radius, radius + (load_w/2)],
        y=[rig_base_y, apex_y, rig_base_y],
        fill='toself', name='Sling Triangle', line=dict(color='orange')
    ))
    
    # Add vertical label for sling height
    fig.add_annotation(x=radius+0.5, y=rig_base_y + (rig_v_height/2), text=f"H={rig_v_height:.2f}m", showarrow=False, textangle=-90)
    # Add diagonal label for sling length
    fig.add_annotation(x=radius - (load_w/4), y=rig_base_y + (rig_v_height/2), text=f"L={s_actual_len:.2f}m", showarrow=False)

    fig.update_layout(height=600, yaxis=dict(scaleanchor="x", scaleratio=1), title="Geometry Working")
    st.plotly_chart(fig, use_container_width=True)

# Safety Check Log
st.subheader("Safety Compliance")
sc1, sc2, sc3 = st.columns(3)
with sc1:
    if total_gross > (reeves * MAX_LINE_PULL): st.error(f"❌ Line Pull Exceeded")
    else: st.success(f"✅ Line Pull OK ({reeves * MAX_LINE_PULL:.1f}t)")
with sc2:
    if headroom < 0.5: st.error("❌ Headroom Critical")
    else: st.success(f"✅ Headroom OK ({headroom:.2f}m)")
with sc3:
    if foul_gap < 0.3: st.error("❌ Boom Interference")
    else: st.success(f"✅ Boom Clearance OK")
