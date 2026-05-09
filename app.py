import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json
import base64
import os

# --- Page Setup (MUST be first) ---
st.set_page_config(page_title="Challengevala Trader Journal", page_icon="📈", layout="wide")

# --- MASTER UNIVERSAL DESIGN CSS ---
st.markdown("""
    <style>
    /* 1. Page Background & Clean Look */
    .stApp { background-color: #fcfcfc; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }

    /* 2. Heading Branding - Green Highlighted */
    .major-title {
        text-align: left; 
        color: #89d957; 
        margin-top: 15px; 
        margin-bottom: 5px; 
        font-size: 38px; 
        font-weight: 800;
        line-height: 1.2;
    }

    /* 3. UNIVERSAL BOX DESIGN (NO BORDER + LOCKED DEPTH) */
    div[data-testid="stPlotlyChart"], .timeline-box, .matrix-container {
        background-color: #ffffff !important;
        border: none !important;
        border-radius: 24px !important;
        box-shadow: 0 10px 40px rgba(0,0,0,0.04), 0 2px 10px rgba(0,0,0,0.01) !important;
        padding: 30px !important;
        margin-bottom: 20px !important;
    }

    /* Metric internal styling - Gradient Colors */
    div[data-testid="stMetric"] {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
    }
    div[data-testid="stMetric"] label { color: #555; font-weight: bold; font-size: 14px; margin-bottom: 5px; }
    div[data-testid="stMetricValue"] > div { 
        background: -webkit-linear-gradient(#89d957, #c9e265);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 32px !important; 
        font-weight: 700 !important; 
    }

    /* 4. Minimalist File Uploader */
    div[data-testid="stFileUploader"] {
        background-color: white;
        border-radius: 20px;
        padding: 10px;
        border: none !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        margin-bottom: 20px;
    }

    /* 5. Timeline styling */
    .timeline-title {color: #89d957; font-weight: bold; font-size: 18px; margin-bottom: 15px;}
    .trade-row { display: flex; align-items: center; margin-bottom: 12px; min-height: 40px; width: 100%; }
    .trade-time { width: 10%; min-width: 70px; font-weight: bold; font-size: 15px; color: #444; }
    .trade-progress-wrapper { width: 70%; background-color: #f0f2f6; border-radius: 12px; height: 28px; position: relative; overflow: hidden; margin: 0 15px; }
    .trade-progress-bar { height: 100%; border-radius: 12px; display: flex; align-items: center; padding-left: 10px; }
    
    .modebar { display: none !important; }
    iframe { overflow: hidden !important; border: none !important; }

    /* Button Styling */
    .stButton>button {
        background: linear-gradient(to right, #89d957, #c9e265) !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 10px 25px !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
logo_path = "logo-full.png"
if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
        st.markdown(f'<img src="data:image/png;base64,{data}" style="max-width: 250px; margin-bottom: 10px;">', unsafe_allow_html=True)

st.markdown('<h1 class="major-title">📈 Elite Quant Dashboard & Auto-Evolving AI</h1>', unsafe_allow_html=True)
st.markdown("---")

# --- API Setup ---
model = None
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash")

# --- Categorization Logic ---
def categorize_asset(name):
    name = str(name).upper()
    if any(x in name for x in ['CE', 'PE', 'C-', 'P-']): return 'Options'
    return 'Futures/Other'

uploaded_files = st.file_uploader("📥 Upload Dhan & Delta CSVs", accept_multiple_files=True, type=['csv'])

if uploaded_files:
    all_data = []
    for f in uploaded_files:
        df = pd.read_csv(f)
        if 'Realised P&L' in df.columns: # Delta
            df['P&L'] = pd.to_numeric(df['Realised P&L'], errors='coerce').fillna(0) * 85
            df['Date_C'] = pd.to_datetime(df['Time'].astype(str).str[:10]).dt.date
            df['Trade_T'] = pd.to_datetime(df['Time'].astype(str).str[:19])
            df['Asset_N'] = df['Contract']
            all_data.append(df[['Date_C', 'Trade_T', 'Asset_N', 'P&L']])
        elif 'Date' in df.columns: # Dhan
            df = df[df['Buy/Sell'].isin(['BUY', 'SELL'])].copy()
            df['P&L'] = df.apply(lambda r: r['Trade Value'] if r['Buy/Sell'] == 'SELL' else -r['Trade Value'], axis=1)
            df['Date_C'] = pd.to_datetime(df['Date']).dt.date
            df['Trade_T'] = pd.to_datetime(df['Time'], format='mixed')
            all_data.append(df[['Date_C', 'Trade_T', 'Name', 'P&L']].rename(columns={'Name':'Asset_N'}))

    if all_data:
        final_df = pd.concat(all_data)
        final_df['Category'] = final_df['Asset_N'].apply(categorize_asset)
        
        tpnl = final_df['P&L'].sum()
        w = len(final_df[final_df['P&L'] > 0])
        l = len(final_df[final_df['P&L'] < 0])
        total = w + l
        wr = (w / total * 100) if total > 0 else 0

        # --- Performance Matrix Inside the Box ---
        st.markdown("<h4 style='color: #89d957; margin-bottom: 15px;'>📊 Combined Performance Matrix</h4>", unsafe_allow_html=True)
        
        # Wrapping metrics STRICTLY inside the container
        with st.container():
            st.markdown('<div class="matrix-container">', unsafe_allow_html=True)
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Total Net P&L", f"₹{tpnl:,.2f}")
            col2.metric("Win Rate", f"{wr:.1f}%")
            col3.metric("Total Trades", total)
            col4.metric("Win Trades", w)
            col5.metric("Loss Trades", l)
            st.markdown('</div>', unsafe_allow_html=True)

        # --- Visual Insights ---
        st.markdown("---")
        st.markdown("<h4 style='color: #89d957; margin-bottom: 15px;'>👁️ Visual Data Insights</h4>", unsafe_allow_html=True)
        
        daily = final_df.groupby('Date_C')['P&L'].sum().reset_index()
        daily['Equity'] = daily['P&L'].cumsum()
        
        fig_eq = px.area(daily, x='Date_C', y='Equity', title="Total Portfolio Growth")
        fig_eq.update_traces(line_color="#89d957", fillcolor="rgba(137, 217, 87, 0.1)")
        fig_eq.update_layout(margin=dict(l=10, r=10, t=40, b=10), plot_bgcolor="white", paper_bgcolor="white") 
        st.plotly_chart(fig_eq, use_container_width=True, config={'displayModeBar': False})
        
        c_g1, c_g2 = st.columns(2)
        with c_g1:
            cat_pnl = final_df.groupby('Category')['P&L'].sum().reset_index()
            fig_cat = px.bar(cat_pnl, x='Category', y='P&L', title="P&L by Category", color=cat_pnl['P&L'] > 0, color_discrete_map={True: "#89d957", False: "#EF553B"})
            fig_cat.update_layout(margin=dict(l=10, r=10, t=40, b=10), showlegend=False, plot_bgcolor="white")
            st.plotly_chart(fig_cat, use_container_width=True)
        with c_g2:
            final_df['Hour'] = final_df['Trade_T'].dt.hour
            hr_pnl = final_df.groupby('Hour')['P&L'].sum().reset_index()
            fig_hr = px.bar(hr_pnl, x='Hour', y='P&L', title="P&L by Hour", color=hr_pnl['P&L'] > 0, color_discrete_map={True: "#89d957", False: "#EF553B"})
            fig_hr.update_layout(margin=dict(l=10, r=10, t=40, b=10), showlegend=False, plot_bgcolor="white")
            st.plotly_chart(fig_hr, use_container_width=True)
