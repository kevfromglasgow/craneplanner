import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

# --- CONFIGURATION ---
st.set_page_config(page_title="Liebherr LTM 1150-5.3 Planner", layout="wide")

# Technical Data extracted from LTM 1150-5.3 Specs
MAX_LINE_PULL = 9.34  # 91.6 kN converted to metric tons 
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
    # Vertical height of the sling triangle
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
st.sidebar.header("1. Load Dimensions")
w_load = st.sidebar.number_input("Load Weight (t)", value=10.0)
load_w = st.sidebar.number_input("Load Width (m)", value=3.0)
load_h = st.sidebar.number_input("Load Height (m)", value=2.0)
fos = st.sidebar.slider("Factor of Safety", 1.0, 1.5, 1.2)

st.sidebar.header("2. Rigging Setup")
num_legs = st.sidebar.selectbox("Sling Legs", [1, 2, 3, 4])
sling_angle = st.sidebar.slider("Sling Angle (from vertical °)", 10, 60, 30)
w_rigging = st.sidebar.number_input("Rigging Weight (t)", value=0.1)

st.sidebar.header("3. Crane Configuration")
hook_choice = st.sidebar.selectbox("Hook Block", list(HOOK_BLOCKS.keys()))
reeves = st.sidebar.number_input("Rope Reeves", 1, HOOK_BLOCKS[hook_choice]['max_lines'], 2)
radius = st.sidebar.slider("Radius (m)", 3, 64, 20) # [cite: 964, 1143]
# Boom length selection based on LTM 1150-5.3 range (12.3m - 66m) 
boom_len = st.sidebar.select_slider("Boom Length (m)", options=[12.3, 16.4, 20.6, 24.7, 28.8, 32.9, 37.0, 41.1, 45.2, 49.4, 53.5, 57.6, 61.7, 66.0])

# --- EXECUTION ---
w_hook = HOOK_BLOCKS[hook_choice]['weight']
total_gross = (w_load + w_hook + w_rigging) * fos
rig_h, s_len, leg_tension = get_rigging_math(load_w, sling_angle, num_legs, total_gross)

# Crane Geometry
boom_angle_rad = math.acos(radius / boom_len)
tip_height = math.sin(boom_angle_rad) * boom_len

# Headroom Check
# Available space = Tip Height - Hook Block Length (~2m) - Rigging Height - Load Height
headroom = tip_height - 2.0 - rig_h - load_h

# --- UI ---
st.title("🏗️ LTM 1150-5.3 Professional Lift Planner")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Gross Load", f"{total_gross:.2f} t")
c2.metric("Sling Length", f"{s_len:.2f} m")
c3.metric("Tension/Leg", f"{leg_tension:.2f} t")
c4.metric("Headroom", f"{headroom:.2f} m", delta_color="inverse")

# Visualization
fig = go.Figure()

# Ground & Crane Hub
fig.add_trace(go.Scatter(x=[-5, radius+5], y=[0, 0], mode='lines', name='Ground', line=dict(color='green')))
fig.add_trace(go.Scatter(x=[0, radius], y=[2, tip_height], mode='lines+markers', name='Main Boom', line=dict(width=10, color='yellow')))

# The Rigging "Hanging" Triangle
# Apex is at the Hook (2m below tip height)
apex_y = tip_height - 2.0
fig.add_trace(go.Scatter(
    x=[radius - (load_w/2), radius, radius + (load_w/2)],
    y=[apex_y - rig_h, apex_y, apex_y - rig_h],
    fill='toself', name='Rigging Triangle', line=dict(color='orange')
))

# The Load Box
fig.add_shape(type="rect", 
              x0=radius-(load_w/2), y0=apex_y - rig_h - load_h, 
              x1=radius+(load_w/2), y1=apex_y - rig_h, 
              fillcolor="gray", line=dict(color="black"))

fig.update_layout(height=700, yaxis=dict(scaleanchor="x", scaleratio=1), title="Side Profile: Hanging Rigging & Load")
st.plotly_chart(fig, use_container_width=True)

# Safety Warnings
if total_gross > (reeves * MAX_LINE_PULL):
    st.error(f"⚠️ LINE PULL EXCEEDED: {reeves} reeves only support {reeves * MAX_LINE_PULL:.2f}t.")
if headroom < 0.5:
    st.error("⚠️ CRITICAL HEADROOM: Load cannot be lifted to this height with current rigging.")
