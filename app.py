import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import math

# --- CONFIGURATION & ASSETS ---
st.set_page_config(page_title="LTM 1150-5.3 Planner", layout="wide")

# Hook Block Data from Technical Specs 
HOOK_BLOCKS = {
    "116.9t (7-sheave)": {"weight": 1.240, "reeves": 14},
    "86.0t (5-sheave)": {"weight": 0.950, "reeves": 10},
    "61.6t (3-sheave)": {"weight": 0.700, "reeves": 7},
    "27.2t (1-sheave)": {"weight": 0.450, "reeves": 3},
    "9.2t (Single line)": {"weight": 0.350, "reeves": 1}
}

# --- FUNCTIONS ---
def get_mode_factor(legs):
    """Uniform Load Method mode factors for chain slings."""
    if legs == 1: return 1.0
    if legs == 2: return 1.0 # Standard logic often treats 2-leg as 1.0 x angle factor
    if legs >= 3: return 2.1 # Standard factor for 3 and 4 leg slings
    return 1.0

def calculate_geometry(radius, boom_length):
    """Calculates boom angle and tip height using Pythagoras."""
    if radius > boom_length:
        return 0, 0
    angle_rad = math.acos(radius / boom_length)
    angle_deg = math.degrees(angle_rad)
    height = math.sqrt(boom_length**2 - radius**2)
    return angle_deg, height

# --- SIDEBAR INPUTS ---
st.sidebar.header("1. Load & Safety")
w_load = st.sidebar.number_input("Load Weight (t)", value=10.0)
fos = st.sidebar.slider("Factor of Safety", 1.0, 1.5, 1.2, step=0.05)
util_limit = st.sidebar.slider("Utilisation Limit (%)", 50, 100, 85)

st.sidebar.header("2. Rigging & Accessories")
legs = st.sidebar.selectbox("Number of Sling Legs", [1, 2, 3, 4])
sling_angle = st.sidebar.slider("Sling Angle (from vertical °)", 0, 60, 30)
w_accessories = st.sidebar.number_input("Accessory Weight (t)", value=0.2)
l_accessories = st.sidebar.number_input("Sling Length (m)", value=4.0)

st.sidebar.header("3. Crane Configuration")
counterweight = st.sidebar.selectbox("Counterweight (t)", [45, 29, 6.2]) # 
hook_choice = st.sidebar.selectbox("Hook Block", list(HOOK_BLOCKS.keys()))
w_hook = HOOK_BLOCKS[hook_choice]["weight"]

st.sidebar.header("4. Lift Coordinates")
input_radius = st.sidebar.slider("Radius (m)", 3, 64, 20) # [cite: 420]
input_boom = st.sidebar.slider("Boom Length (m)", 12.3, 66.0, 32.9) # [cite: 424]

# --- LOGIC ---
# 1. Total Weight
total_lift_weight = (w_load + w_accessories + w_hook) * fos

# 2. Sling Tension
mode_f = get_mode_factor(legs)
# Tension per leg = (Total weight / (num_legs * cos(angle)))
# Using Uniform Load Method for 3/4 legs
tension_per_leg = (total_lift_weight / mode_f) / math.cos(math.radians(sling_angle))

# 3. Crane Geometry
boom_angle, tip_height = calculate_geometry(input_radius, input_boom)
headroom = tip_height - (l_accessories * math.cos(math.radians(sling_angle))) - 2.0 # 2m approx for hook block

# --- MAIN UI ---
st.title("🏗️ Liebherr LTM 1150-5.3 Crane Planner")

col1, col2, col3 = st.columns(3)
col1.metric("Total Weight (Incl. FOS)", f"{total_lift_weight:.2f} t")
col2.metric("Tension Per Leg", f"{tension_per_leg:.2f} t")
col3.metric("Boom Angle", f"{boom_angle:.1f}°")

tab_side, tab_top = st.tabs(["📐 Side-on View", "🌍 Top-down View"])

with tab_side:
    # 2D Side View Visualization
    fig = go.Figure()
    
    # Draw Ground
    fig.add_shape(type="line", x0=-5, y0=0, x1=input_radius+10, y1=0, line=dict(color="Green", width=3))
    
    # Draw Boom
    fig.add_trace(go.Scatter(x=[0, input_radius], y=[2, tip_height], mode='lines+markers', name="Main Boom", line=dict(width=8, color='Yellow')))
    
    # Draw Load
    fig.add_trace(go.Scatter(x=[input_radius, input_radius], y=[tip_height, tip_height-2, tip_height-4], 
                             mode='lines+markers', name="Rigging & Load", line=dict(color='Black', dash='dash')))
    
    fig.update_layout(title="Side Elevation (Headroom Check)", xaxis_range=[-10, 70], yaxis_range=[0, 80], height=600)
    st.plotly_chart(fig, use_container_width=True)
    
    if headroom < 1.0:
        st.error(f"⚠️ LOW HEADROOM: {headroom:.2f}m. Increase boom length or shorten slings.")
    else:
        st.success(f"Headroom Clearance: {headroom:.2f}m")

with tab_top:
    st.subheader("Outrigger & Slew Plan")
    # Simple Top-down outrigger base visualization
    # LTM 1150 max base: 9.3m x 8.3m [cite: 19]
    fig_top = go.Figure()
    
    # Outrigger rectangle
    fig_top.add_shape(type="rect", x0=-4.15, y0=-4.65, x1=4.15, y1=4.65, line=dict(color="Red"), name="Outrigger Base")
    
    # Boom pointer (Slew)
    slew_angle = st.slider("Slew Angle (°)", 0, 360, 0)
    slew_rad = math.radians(slew_angle)
    bx = input_radius * math.sin(slew_rad)
    by = input_radius * math.cos(slew_rad)
    
    fig_top.add_trace(go.Scatter(x=[0, bx], y=[0, by], mode='lines', name="Boom Direction", line=dict(width=5, color='Yellow')))
    
    fig_top.update_layout(title="Top Down (Outrigger Base)", xaxis_range=[-30, 30], yaxis_range=[-30, 30], height=600)
    st.plotly_chart(fig_top, use_container_width=True)

st.warning("Note: This tool uses calculated geometry. Always verify against the official Liebherr LICCON system before execution. [cite: 1170]")