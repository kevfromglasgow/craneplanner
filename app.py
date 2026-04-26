import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

# --- CONFIGURATION ---
st.set_page_config(page_title="LTM 1150-5.3: Hoist & Travel Planner", layout="wide")

# Technical Data from Liebherr LTM 1150-5.3 Specs
TOTAL_ROPE_LENGTH = 250.0  # 
MAX_LINE_PULL = 9.34       # 91.6 kN [cite: 146]

HOOK_BLOCKS = {
    "116.9t (7-sheave)": {"weight": 1.240, "max_lines": 14, "length": 1.5}, 
    "86.0t (5-sheave)": {"weight": 0.950, "max_lines": 10, "length": 1.2},  
    "61.6t (3-sheave)": {"weight": 0.700, "max_lines": 7, "length": 1.0},   
    "27.2t (1-sheave)": {"weight": 0.450, "max_lines": 3, "length": 0.8},   
    "9.2t (Single line)": {"weight": 0.350, "max_lines": 1, "length": 0.6}  
}

# --- SIDEBAR ---
st.sidebar.header("1. Load & Safety")
w_load = st.sidebar.number_input("Load Weight (t)", value=10.0)
load_w = st.sidebar.number_input("Width of Load (m)", value=3.0)
load_h = st.sidebar.number_input("Height of Load (m)", value=2.0)
fos = st.sidebar.slider("Factor of Safety", 1.0, 1.5, 1.2, step=0.05)

st.sidebar.header("2. Hoist & Rigging")
# User defines how high they want to lift the load
lift_height = st.sidebar.slider("Current Load Height Above Ground (m)", 0.0, 70.0, 5.0)
sling_l_input = st.sidebar.number_input("Sling Length (L) (m)", value=6.0, step=0.5)
sling_angle = st.sidebar.slider("Sling Angle (α) (°)", 10, 60, 30)

st.sidebar.header("3. Crane Configuration")
hook_choice = st.sidebar.selectbox("Hook Block", list(HOOK_BLOCKS.keys()))
reeves = st.sidebar.number_input("Parts of Line (Reeves)", 1, HOOK_BLOCKS[hook_choice]['max_lines'], 4)
boom_len = st.sidebar.select_slider("Boom Length (m)", options=[12.3, 16.4, 20.6, 24.7, 28.8, 32.9, 37.0, 41.1, 45.2, 49.4, 53.5, 57.6, 61.7, 66.0])
radius = st.sidebar.slider("Radius (m)", 3.0, float(boom_len) - 1.0, 15.0)

# --- CALCULATIONS ---
angle_rad = math.radians(sling_angle)
rig_v_height = sling_l_input * math.cos(angle_rad)
reached_half_width = sling_l_input * math.sin(angle_rad)

# Weight & Tension
w_hook = HOOK_BLOCKS[hook_choice]['weight']
total_gross = (w_load + w_hook + 0.1) * fos
mode_f = (2.1 if sling_angle <= 45 else 1.5) if reeves > 2 else 1.4
leg_tension = total_gross / mode_f

# Vertical Geometry
tip_h = math.sqrt(boom_len**2 - radius**2)
block_len = HOOK_BLOCKS[hook_choice]['length']

# CURRENT ROPE HANG CALCULATION
# Distance from tip to the bottom of the load is (Tip Height - Current Lift Height)
current_total_hang = tip_h - lift_height
# The "Rope Gap" is the remaining vertical cable between block and slings
rope_gap = current_total_hang - block_len - rig_v_height - load_h
# Actual used cable length (vertical)
rope_used_per_part = tip_h - lift_height + load_h + rig_v_height + block_len
total_cable_out = rope_used_per_part * reeves

# --- UI DASHBOARD ---
st.title("🏗️ LTM 1150-5.3: Hoist Travel & Cable Limits")

col_metrics, col_viz = st.columns([1, 2])

with col_metrics:
    st.subheader("📊 Hoist Metrics")
    st.metric("Total Cable Paid Out", f"{total_cable_out:.1f} m", help="Total rope used across all reeves")
    st.metric("Rope-to-Sling Gap", f"{rope_gap:.2f} m", help="Distance between hook block and slings")
    
    # 250m Limit Check
    if total_cable_out > TOTAL_ROPE_LENGTH:
        st.error(f"❌ OUT OF ROPE: Need {total_cable_out:.1f}m but only {TOTAL_ROPE_LENGTH}m available.")
    else:
        st.success(f"✅ Cable Remaining: {TOTAL_ROPE_LENGTH - total_cable_out:.1f} m")

    st.markdown("---")
    st.write(f"**Reeving Capacity:** {reeves * MAX_LINE_PULL:.1f} t")
    st.write(f"**Max Potential Height:** {tip_h:.1f} m")

with col_viz:
    fig = go.Figure()
    # Boom & Ground
    fig.add_trace(go.Scatter(x=[-2, radius+5], y=[0,0], mode='lines', line=dict(color='green'), name="Ground"))
    fig.add_trace(go.Scatter(x=[0, radius], y=[2.3, tip_h], mode='lines+markers', line=dict(width=10, color='yellow'), name="Boom"))
    
    # HOIST LINE (From Tip to Hook Block)
    fig.add_trace(go.Scatter(x=[radius, radius], y=[tip_h, tip_h - 2.0 - rope_gap], mode='lines', line=dict(color='black', dash='dot'), name="Hoist Rope"))
    
    # RIGGING TRIANGLE
    apex_y = lift_height + load_h + rig_v_height
    fig.add_trace(go.Scatter(
        x=[radius - reached_half_width, radius, radius + reached_half_width],
        y=[lift_height + load_h, apex_y, lift_height + load_h],
        fill='toself', name='Slings', line=dict(color='orange')
    ))
    
    # LOAD
    fig.add_shape(type="rect", x0=radius-(load_w/2), y0=lift_height, x1=radius+(load_w/2), y1=lift_height+load_h, fillcolor="gray")

    fig.update_layout(height=650, yaxis=dict(scaleanchor="x", scaleratio=1), title="Dynamic Lift Profile")
    st.plotly_chart(fig, use_container_width=True)

# Compliance Summary
if rope_gap < 0.2:
    st.error("❌ TWO-BLOCKING RISK: Hook block is hitting the slings/load. Lower the load or shorten slings.")
