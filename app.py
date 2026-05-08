import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
from datetime import datetime

# --- Professional Theme Configuration ---
st.set_page_config(page_title="Quant-Intel Pro Terminal", page_icon="⚡", layout="wide")

# Custom CSS for Professional UI
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Metric Card Styling */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
    }
    
    .stMetric {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 15px !important;
        border-left: 5px solid #4B6BFB;
    }
    
    /* Section Headers */
    .section-header {
        font-size: 24px;
        font-weight: 700;
        color: #1a1a1a;
        margin-bottom: 20px;
        border-bottom: 2px solid #4B6BFB;
        padding-bottom: 5px;
        width: fit-content;
    }
    
    /* Sidebar Styling */
    .css-1d391kg {
        background-color: #f1f3f6;
    }
    
    /* Button Styling */
    .stButton>button {
        background-color: #4B6BFB;
        color: white;
        border-radius: 8px;
        width: 100%;
        font-weight: 600;
        height: 3em;
        border: none;
    }
    </style>
""", unsafe_allow_html=True)

# --- AI Setup (Auto-Detect Model) ---
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Finding the best available model
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model_name = next((m for m in available_models if 'flash' in m or 'pro' in m), available_models[0])
        model = genai.GenerativeModel(model_name)
except Exception as e:
    st.sidebar.error(f"AI Core Offline: {e}")

# --- Sidebar Controls ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2422/2422796.png", width=100)
    st.title("Pro Settings")
    st.markdown("---")
    inr_rate = st.number_input("USD to INR Rate", value=85.0)
    st.info("💡 Note: Upload Dhan (Equity/F&O) or Delta (Crypto) CSVs to populate the terminal.")

# --- Main Terminal ---
st.title("⚡ Quant-Intel Pro Terminal")
st.markdown("<p style='color: #666;'>Institutional Grade Trading Analytics & AI Oversight</p>", unsafe_allow_html=True)

uploaded_files = st.file_uploader("📥 Drag & Drop Institutional Ledger (CSV)", accept_multiple_files=True, type=['csv'])

if uploaded_files:
    df_list = [pd.read_csv(f) for f in uploaded_files]
    df = pd.concat(df_list, ignore_index=True)
    
    # ---------------------------------------------
    # DATA PROCESSING ENGINE
    # ---------------------------------------------
    df['P&L_Clean'] = 0.0
    df['Date_Clean'] = pd.NaT
    analytics_df = pd.DataFrame()

    if 'Time' in df.columns and 'Realised P&L' in df.columns:
        # DELTA ENGINE
        df['Date_Clean'] = pd.to_datetime(df['Time'].astype(str).str[:10], errors='coerce').dt.date
        df['P&L_Clean'] = pd.to_numeric(df['Realised P&L'], errors='coerce').fillna(0) * inr_rate
        analytics_df = df[df['P&L_Clean'] != 0].copy()
        analytics_df['Asset'] = analytics_df['Contract']
        analytics_df['Trade_Time'] = pd.to_datetime(analytics_df['Time'], errors='coerce')

    elif 'Date' in df.columns and 'Trade Value' in df.columns:
        # DHAN ENGINE
        df = df[df['Buy/Sell'].astype(str).str.upper().isin(['BUY', 'SELL'])].copy()
        df['Date_Clean'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        df['Cashflow'] = df.apply(lambda r: r['Trade Value'] if str(r['Buy/Sell']).upper() == 'SELL' else -r['Trade Value'], axis=1)
        
        grouped = df.groupby(['Date_Clean', 'Name']).agg({'Cashflow': 'sum', 'Time': 'max'}).reset_index()
        analytics_df = grouped[grouped['Cashflow'] != 0].copy()
        analytics_df.rename(columns={'Cashflow': 'P&L_Clean', 'Name': 'Asset'}, inplace=True)
        analytics_df['Trade_Time'] = pd.to_datetime(analytics_df['Time'], format='mixed', errors='coerce')

    if not analytics_df.empty:
        # Calculate Advanced Stats
        total_pnl = analytics_df['P&L_Clean'].sum()
        wins_df = analytics_df[analytics_df['P&L_Clean'] > 0]
        losses_df = analytics_df[analytics_df['P&L_Clean'] < 0]
        win_rate = (len(wins_df) / len(analytics_df) * 100)
        avg_win = wins_df['P&L_Clean'].mean() if not wins_df.empty else 0
        avg_loss = abs(losses_df['P&L_Clean'].mean()) if not losses_df.empty else 0
        profit_factor = (wins_df['P&L_Clean'].sum() / abs(losses_df['P&L_Clean'].sum())) if not losses_df.empty else 0

        # --- EXECUTIVE SUMMARY ---
        st.markdown("<div class='section-header'>📊 Executive Summary</div>", unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Net Realized P&L", f"₹{total_pnl:,.2f}", f"{total_pnl/1000:.1f}k")
        m2.metric("Hit Ratio (Win %)", f"{win_rate:.1f}%")
        m3.metric("Profit Factor", f"{profit_factor:.2f}x")
        m4.metric("Avg Win/Loss Ratio", f"{(avg_win/avg_loss if avg_loss > 0 else 0):.2f}")

        # --- ADVANCED ANALYTICS (Charts) ---
        st.markdown("---")
        col_main, col_side = st.columns([2, 1])
        
        with col_main:
            # Main Equity Curve
            daily = analytics_df.groupby('Date_Clean')['P&L_Clean'].sum().reset_index()
            daily['Cumulative'] = daily['P&L_Clean'].cumsum()
            fig_equity = px.area(daily, x='Date_Clean', y='Cumulative', 
                                title="<b>Cumulative Growth Path</b>",
                                color_discrete_sequence=['#4B6BFB'])
            fig_equity.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig_equity, use_container_width=True)

        with col_side:
            # Distribution of Profits/Losses
            fig_dist = px.histogram(analytics_df, x='P&L_Clean', nbins=20, 
                                   title="<b>P&L Distribution</b>",
                                   color_discrete_sequence=['#333'])
            st.plotly_chart(fig_dist, use_container_width=True)

        st.markdown("---")
        col_c1, col_c2 = st.columns(2)
        
        with col_c1:
            asset_data = analytics_df.groupby('Asset')['P&L_Clean'].sum().sort_values().reset_index()
            fig_asset = px.bar(asset_data, y='Asset', x='P&L_Clean', orientation='h',
                              title="<b>Profitability by Instrument</b>",
                              color='P&L_Clean', color_continuous_scale='RdYlGn')
            st.plotly_chart(fig_asset, use_container_width=True)
            
        with col_c2:
            analytics_df['Hour'] = analytics_df['Trade_Time'].dt.hour
            hour_data = analytics_df.groupby('Hour')['P&L_Clean'].sum().reset_index()
            fig_hour = px.line(hour_data, x='Hour', y='P&L_Clean', markers=True,
                              title="<b>Market Hourly Edge Analysis</b>",
                              color_discrete_sequence=['#4B6BFB'])
            st.plotly_chart(fig_hour, use_container_width=True)

        # --- AI QUANT INSIGHTS ---
        st.markdown("<div class='section-header'>🧠 AI Quant Oversight</div>", unsafe_allow_html=True)
        if st.button("RUN DEEP SYSTEM AUDIT"):
            if model:
                with st.spinner("Executing Data Forensic Analysis..."):
                    ai_input = analytics_df[['Date_Clean', 'Trade_Time', 'Asset', 'P&L_Clean']].tail(40).to_string()
                    prompt = f"""
                    You are an institutional Quant Risk Manager. Analyze the following trading footprint for high-risk behaviors.
                    
                    Data Ledger:
                    {ai_input}
                    
                    Provide a forensic report in a professional Markdown Table with these columns:
                    | Pattern Detected | Evidence (Time/Asset) | Risk Level | Mitigation Strategy |
                    
                    Followed by ONE 'Institutional Grade Rule' in Hinglish. 
                    Be brutal and precise. No generic advice.
                    """
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
            else:
                st.error("AI Model connection error.")

else:
