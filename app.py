import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json
import base64
import os

# --- Page Setup (MUST be first) ---
st.set_page_config(page_title="Challengevala Trader Journal", page_icon="📈", layout="wide")

# --- MASTER STRICT CSS (Logo Container Settle Kiya Hai) ---
st.markdown("""
    <style>
    /* 1. Background & Global Font */
    .stApp { background-color: #fcfcfc; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }

    /* 2. LOGO CONTAINER FIX (Proper Padding & No Cut) */
    .block-container { padding-top: 1.5rem !important; }
    
    .logo-img-container {
        display: flex;
        justify-content: flex-start;
        align-items: flex-start;
        width: 100%;
        margin-bottom: 0px;
        padding-left: 0px;
    }
    
    .logo-img {
        width: 120px !important; /* Size fixed to small */
        height: auto !important;
        display: block !important;
        margin: 0 !important;
        object-fit: contain !important;
        padding-top: 10px !important; /* Spacing from top to avoid cutting */
    }

    /* Heading Branding matching Brand Green */
    .major-title {
        text-align: left; 
        background: -webkit-linear-gradient(#89d957, #c9e265);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-top: 5px; 
        margin-bottom: 5px; 
        font-size: 38px; 
        font-weight: 800;
        line-height: 1.2;
    }

    /* 3. Metrics Layout */
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] { padding: 0 10px; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px !important;
        border-radius: 20px !important;
        border: 1px solid #eeeeee !important;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05), 0 4px 10px rgba(0,0,0,0.02) !important;
        display: flex;
        flex-direction: column;
        justify-content: center;
        min-height: 120px;
    }
    div[data-testid="stMetric"] label { color: #555; font-weight: bold; font-size: 14px; margin-bottom: 5px; }
    div[data-testid="stMetricValue"] > div { 
        background: -webkit-linear-gradient(#89d957, #c9e265);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 28px !important; 
        font-weight: 700 !important; 
    }

    /* 4. Fixing Vertical Scrollbars on Charts */
    div[data-testid="stPlotlyChart"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 20px;
        border: 1px solid #eeeeee;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05) !important;
        margin-bottom: 20px;
        overflow: hidden !important; 
    }
    iframe { overflow: hidden !important; border: none !important; }

    /* 5. Timelines */
    .timeline-box {
        background-color: #ffffff;
        padding: 25px;
        border-radius: 20px;
        border: 1px solid #eeeeee;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        width: 100%;
        overflow: hidden;
    }
    .modebar { display: none !important; }
    hr { margin: 1em 0 !important; }
    </style>
""", unsafe_allow_html=True)

# --- HEADER (LOGO + HEADING BELOW) ---
logo_path = "logo-full.png"
if os.path.exists(logo_path):
    with open(logo_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
        # Strictly using HTML for Logo placement to avoid Streamlit's container cutoff
        st.markdown(f'''
            <div class="logo-img-container">
                <img src="data:image/png;base64,{encoded_string}" class="logo-img">
            </div>
        ''', unsafe_allow_html=True)

st.markdown('<h1 class="major-title">📈 Elite Quant Dashboard & Auto-Evolving AI</h1>', unsafe_allow_html=True)
st.markdown("---")

# --- API Setup ---
model = None
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash")

uploaded_files = st.file_uploader("📥 Upload CSVs", accept_multiple_files=True, type=['csv'])

if uploaded_files:
    all_data = []
    for f in uploaded_files:
        df = pd.read_csv(f)
        if 'Realised P&L' in df.columns: # Delta
            df['P&L'] = pd.to_numeric(df['Realised P&L'], errors='coerce').fillna(0) * 85
            df['Date'] = pd.to_datetime(df['Time'].str[:10]).dt.date
            all_data.append(df[['Date', 'P&L']])
        elif 'Date' in df.columns: # Dhan
            df = df[df['Buy/Sell'].isin(['BUY', 'SELL'])].copy()
            df['P&L'] = df.apply(lambda r: r['Trade Value'] if r['Buy/Sell'] == 'SELL' else -r['Trade Value'], axis=1)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            all_data.append(df[['Date', 'P&L']])

    if all_data:
        final_df = pd.concat(all_data)
        
        total_pnl = final_df['P&L'].sum()
        wins = len(final_df[final_df['P&L'] > 0])
        losses = len(final_df[final_df['P&L'] < 0])
        total_trades = wins + losses 
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        st.markdown("<h4 style='color: #1976d2;'>📊 Performance Matrix</h4>", unsafe_allow_html=True)
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Net P&L", f"₹{total_pnl:,.2f}")
        m2.metric("Win Rate", f"{win_rate:.1f}%")
        m3.metric("Total Trades", total_trades)
        m4.metric("Wins", wins)
        m5.metric("Losses", losses)

        # --- Visuals ---
        st.markdown("---")
        st.markdown("<h4 style='color: #1976d2;'>👁️ Total Portfolio Growth</h4>", unsafe_allow_html=True)
        
        daily = final_df.groupby('Date')['P&L'].sum().reset_index()
        daily['Equity'] = daily['P&L'].cumsum()
        
        fig_eq = px.area(daily, x='Date', y='Equity')
        fig_eq.update_traces(line_color="#89d957", fillcolor="rgba(137, 217, 87, 0.1)")
        fig_eq.update_layout(margin=dict(l=10, r=10, t=10, b=10), hovermode=False, plot_bgcolor="white") 
        st.plotly_chart(fig_eq, use_container_width=True, config={'displayModeBar': False})
