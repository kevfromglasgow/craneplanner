import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

# --- CONFIGURATION ---
st.set_page_config(page_title="LTM 1150-5.3 Fixed-Sling Planner", layout="wide")

MAX_LINE_PULL = 9.34 # From specs: 91.6 kN [cite: 146]
HOOK_BLOCKS = {
    "116.9t (7-sheave)": {"weight": 1.240, "max_lines": 14, "length": 1.5}, 
    "86.0t (5-sheave)": {"weight": 0.950, "max_lines": 10, "length": 1.2},  
    "61.6t (3-sheave)": {"weight": 0.700, "max_lines": 7, "length": 1.0},   
    "27.2t (1-sheave)": {"weight": 0.450, "max_lines": 3, "length": 0.8},   
    "9.2t (Single line)": {"weight": 0.350, "max_lines": 1, "length": 0.6}  
}

# --- SIDEBAR ---
st.sidebar.header("1. Load & Safety")
w_load = st.sidebar.number_input("Weight of Load (t)", value=10.0)
load_w = st.sidebar.number_input("Width of Load (m)", value=3.0)
load_h = st.sidebar.number_input("Height of Load (m)", value=2.0)
fos = st.sidebar.slider("Factor of Safety", 1.0, 1.5, 1.2, step=0.05)

st.sidebar.header("2. Rigging (Fixed Sling Mode)")
# User sets the actual length of the chains available
sling_l_input = st.sidebar.number_input("Available Sling Length (L) (m)", value=10.0, step=0.5)
sling_angle = st.sidebar.slider("Sling Angle from Vertical (α) (°)", 10, 60, 45)

num_legs = st.sidebar.selectbox("Number of Sling Legs", [1, 2, 3, 4])
w_rigging = st.sidebar.number_input("Weight of Rigging (t)", value=0.1)
master_link_gap = st.sidebar.slider("Hook to Sling Apex Gap (m)", 0.2, 3.0, 0.5)

st.sidebar.header("3. Crane Setup")
hook_choice = st.sidebar.selectbox("Hook Block", list(HOOK_BLOCKS.keys()))
reeves = st.sidebar.number_input("Rope Reeves", 1, HOOK_BLOCKS[hook_choice]['max_lines'], 2)
boom_len = st.sidebar.select_slider("Boom Length (m)", options=[12.3, 16.4, 20.6, 24.7, 28.8, 32.9, 37.0, 41.1, 45.2, 49.4, 53.5, 57.6, 61.7, 66.0])
radius = st.sidebar.slider("Radius (m)", 3.0, float(boom_len) - 1.0, 15.0)

# --- CALCULATIONS ---
w_hook = HOOK_BLOCKS[hook_choice]['weight']
block_len = HOOK_BLOCKS[hook_choice]['length']
total_gross = (w_load + w_hook + w_rigging) * fos
angle_rad = math.radians(sling_angle)

# Calculate Vertical Height based on Fixed Hypotenuse (L)
rig_v_height = sling_l_input * math.cos(angle_rad)
# Calculate reached width (to check if it actually spans the load)
reached_half_width = sling_l_input * math.sin(angle_rad)

# Mode Factor Logic (Uniform Load Method)
if num_legs == 2:
    mode_f = 1.4 if sling_angle <= 45 else 1.0
elif num_legs >= 3:
    mode_f = 2.1 if sling_angle <= 45 else 1.5
else:
    mode_f = 1.0
leg_tension = total_gross / mode_f

# Crane Geometry
tip_h = math.sin(math.acos(radius / boom_len)) * boom_len
apex_y = tip_h - block_len - master_link_gap
rig_base_y = apex_y - rig_v_height
headroom = rig_base_y - load_h

# --- UI DASHBOARD ---
st.title("🏗️ LTM 1150-5.3: Fixed Sling Planning")

col_math, col_viz = st.columns([1, 2])

with col_math:
    st.subheader("📐 Rigging Verification")
    
    # Validation: Is the sling long enough to reach the load width at this angle?
    if reached_half_width < (load_w / 2):
        st.error(f"❌ INVALID RIGGING: {sling_l_input}m slings at {sling_angle}° cannot reach a {load_w}m width. Increase angle or sling length.")
        st.info(f"Slings only reach a width of {reached_half_width*2:.2f}m")
    else:
        st.success(f"✅ Rigging Spans Load: Reaches {reached_half_width*2:.2f}m width.")

    st.markdown(f"""
    **Calculation Results:**
    * **Calculated Rigging Height ($H$):** {rig_v_height:.2f} m
    * **Rope Hang (Headroom Gap):** {master_link_gap:.2f} m
    * **WLL Required per leg:** {total_gross / mode_f:.2f} t
    
    **Geometry Formula:**
    $H = {sling_l_input} \\times \\cos({sling_angle}^\\circ)$
    """)

with col_viz:
    fig = go.Figure()
    # Ground/Boom
    fig.add_trace(go.Scatter(x=[-2, radius+5], y=[0,0], mode='lines', line=dict(color='green'), name="Ground"))
    fig.add_trace(go.Scatter(x=[0, radius], y=[2.3, tip_h], mode='lines+markers', line=dict(width=10, color='yellow'), name="Boom"))
    
    # Rigging Triangle
    fig.add_trace(go.Scatter(
        x=[radius - reached_half_width, radius, radius + reached_half_width],
        y=[rig_base_y, apex_y, rig_base_y],
        fill='toself', name='Rigging Triangle', line=dict(color='orange')
    ))
    
    # Headroom Labels
    fig.add_annotation(x=radius+2, y=tip_h - (block_len/2), text="Hook Block", showarrow=True)
    fig.add_annotation(x=radius+2, y=apex_y + (master_link_gap/2), text=f"Rope Hang: {master_link_gap}m", showarrow=True)

    fig.update_layout(height=650, yaxis=dict(scaleanchor="x", scaleratio=1), title="Visual Checklist")
    st.plotly_chart(fig, use_container_width=True)

# Safety Summary
st.subheader("Crane Compliance")
sc1, sc2, sc3 = st.columns(3)
with sc1:
    line_cap = reeves * MAX_LINE_PULL
    if total_gross > line_cap: st.error(f"❌ Line Pull Exceeded ({line_cap:.1f}t max)")
    else: st.success(f"✅ Line Pull OK ({line_cap:.1f}t)")
with sc2:
    if headroom < 0.5: st.error(f"❌ Headroom Critical ({headroom:.2f}m)")
    else: st.success(f"✅ Headroom OK ({headroom:.2f}m)")
with sc3:
    # Foul Check
    dist_to_boom = rig_base_y / math.tan(math.acos(radius / boom_len))
    foul_gap = (radius - dist_to_boom) - (load_w / 2)
    if foul_gap < 0.3: st.error("❌ Boom Interference")
    else: st.success(f"✅ Boom Clearance OK")
