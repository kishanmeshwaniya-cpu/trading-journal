import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json
import base64
import os

# --- Page Setup ---
st.set_page_config(page_title="Challengevala Trader Journal", page_icon="📈", layout="wide")

# --- MASTER UNIVERSAL DESIGN CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #fcfcfc; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }

    /* BLACK Heading for Elite Quant Dashboard */
    .major-title {
        text-align: left; 
        color: #000000; /* Strictly Black */
        margin-top: 15px; 
        margin-bottom: 5px; 
        font-size: 38px; 
        font-weight: 800;
        line-height: 1.2;
    }

    /* GREEN GRADIENT for other Highlights */
    .highlight-green {
        text-align: left; 
        background: -webkit-linear-gradient(#89d957, #c9e265);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-top: 15px; 
        margin-bottom: 5px; 
        font-size: 38px; 
        font-weight: 800;
        line-height: 1.2;
    }

    /* BLUE GRADIENT for Combined Performance Matrix Heading */
    .matrix-title-blue {
        background: -webkit-linear-gradient(#000000, #1e4ae6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 24px;
        font-weight: 800;
        margin-bottom: 15px;
        display: inline-block;
    }

    /* THE WHITE BOX DESIGN */
    .matrix-box {
        background-color: #ffffff !important;
        border-radius: 24px !important;
        box-shadow: 0 10px 40px rgba(0,0,0,0.04), 0 2px 10px rgba(0,0,0,0.01) !important;
        padding: 40px 20px !important;
        margin-bottom: 30px !important;
        display: flex;
        justify-content: space-around;
        align-items: center;
        text-align: center;
        width: 100%;
    }

    /* Individual Data Item Styling Inside Box (Blue-Black Gradient) */
    .metric-item { flex: 1; }
    .metric-label { color: #555; font-weight: bold; font-size: 14px; margin-bottom: 8px; }
    .metric-value { 
        background: -webkit-linear-gradient(#000000, #1e4ae6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 30px; 
        font-weight: 800; 
    }

    /* Universal Box for Charts */
    div[data-testid="stPlotlyChart"] {
        background-color: #ffffff !important;
        border-radius: 24px !important;
        box-shadow: 0 10px 40px rgba(0,0,0,0.04), 0 2px 10px rgba(0,0,0,0.01) !important;
        padding: 20px !important;
        margin-bottom: 20px !important;
    }

    .modebar { display: none !important; }
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

# --- File Logic ---
uploaded_files = st.file_uploader("📥 Upload CSVs", accept_multiple_files=True, type=['csv'])

if uploaded_files:
    all_data = []
    for f in uploaded_files:
        df = pd.read_csv(f)
        if 'Realised P&L' in df.columns:
            df['P&L'] = pd.to_numeric(df['Realised P&L'], errors='coerce').fillna(0) * 85
            df['Date'] = pd.to_datetime(df['Time'].astype(str).str[:10]).dt.date
            all_data.append(df[['Date', 'P&L']])
        elif 'Date' in df.columns:
            df = df[df['Buy/Sell'].isin(['BUY', 'SELL'])].copy()
            df['P&L'] = df.apply(lambda r: r['Trade Value'] if r['Buy/Sell'] == 'SELL' else -r['Trade Value'], axis=1)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            all_data.append(df[['Date', 'P&L']])

    if all_data:
        final_df = pd.concat(all_data)
        tpnl = final_df['P&L'].sum()
        w = len(final_df[final_df['P&L'] > 0])
        l = len(final_df[final_df['P&L'] < 0])
        total = w + l
        wr = (w / total * 100) if total > 0 else 0

        # --- THE MATRIX HEADING (BLUE GRADIENT) ---
        st.markdown('<div class="matrix-title-blue">📊 Combined Performance Matrix</div>', unsafe_allow_html=True)
        
        # Matrix Box with Blue-Black Values
        st.markdown(f"""
            <div class="matrix-box">
                <div class="metric-item">
                    <div class="metric-label">Total Net P&L</div>
                    <div class="metric-value">₹{tpnl:,.2f}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Win Rate</div>
                    <div class="metric-value">{wr:.1f}%</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Total Trades</div>
                    <div class="metric-value">{total}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Win Trades</div>
                    <div class="metric-value">{w}</div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Loss Trades</div>
                    <div class="metric-value">{l}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # --- Visual Data Insights (Green Highlights) ---
        st.markdown("---")
        st.markdown('<div class="highlight-green">👁️ Visual Data Insights</div>', unsafe_allow_html=True)
        
        daily = final_df.groupby('Date')['P&L'].sum().reset_index()
        daily['Equity'] = daily['P&L'].cumsum()
        
        fig = px.area(daily, x='Date', y='Equity', title="Total Portfolio Growth")
        fig.update_traces(line_color="#89d957", fillcolor="rgba(137, 217, 87, 0.1)")
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", margin=dict(l=10, r=10, t=40, b=10)) 
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
