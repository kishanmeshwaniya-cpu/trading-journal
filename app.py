import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json
import base64
import os

# --- Page Setup ---
st.set_page_config(page_title="Challengevala Trader Journal", page_icon="📈", layout="wide")

# --- ULTRA MINIMALIST CSS (No Borders, Proper Depth) ---
st.markdown("""
    <style>
    /* 1. Background & Global Font */
    .stApp { background-color: #f8f9fa; font-family: 'Inter', sans-serif; }

    /* 2. Remove Borders and add Smooth Shadows & Corners */
    /* Metric boxes & Charts unified */
    div[data-testid="stMetric"], div[data-testid="stPlotlyChart"], .timeline-box {
        background-color: #ffffff !important;
        border: none !important; /* Strictly No Borders */
        border-radius: 24px !important; /* Smooth Rounded Corners */
        /* High-end soft depth shadow */
        box-shadow: 0 10px 30px rgba(0,0,0,0.04), 0 4px 8px rgba(0,0,0,0.02) !important;
        padding: 24px !important;
        margin-bottom: 20px !important;
    }

    /* 3. Heading Alignment & Size */
    .major-title {
        text-align: left; 
        color: #1976d2; 
        font-size: 36px; 
        font-weight: 800;
        margin-top: 10px;
        margin-bottom: 20px;
    }

    /* 4. Metric Text Colors (Matching Brand) */
    div[data-testid="stMetricValue"] > div { color: #1976d2 !important; font-weight: 700 !important; }
    div[data-testid="stMetric"] label { color: #666 !important; font-size: 15px !important; }

    /* 5. Minimalist File Uploader (No border, light depth) */
    div[data-testid="stFileUploader"] {
        background-color: white;
        border: none;
        border-radius: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }

    /* 6. Strict Timeline Table (No internal borders) */
    .trade-row { display: flex; align-items: center; margin-bottom: 12px; min-height: 40px; width: 100%; }
    .trade-time { width: 10%; min-width: 70px; font-weight: 600; color: #444; }
    .trade-progress-wrapper { 
        width: 70%; background-color: #f0f2f6; border-radius: 12px; 
        height: 28px; position: relative; overflow: hidden; margin: 0 15px; 
    }
    .trade-progress-bar { height: 100%; border-radius: 12px; display: flex; align-items: center; padding-left: 10px; }
    .trade-pnl { width: 20%; min-width: 130px; text-align: right; font-weight: 700; font-size: 18px; }
    
    /* 7. Hide Plotly modebar & Overflow Fix */
    .modebar { display: none !important; }
    div[data-testid="stPlotlyChart"] { overflow: hidden !important; }

    /* Remove default Streamlit padding from top */
    .block-container { padding-top: 2rem !important; }
    </style>
""", unsafe_allow_html=True)

# --- HEADER (LOGO THEN HEADING BELOW) ---
logo_path = "logo-full.png"
if os.path.exists(logo_path):
    with open(logo_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
        st.markdown(f'<img src="data:image/png;base64,{encoded_string}" style="max-width: 240px; margin-bottom: 10px;">', unsafe_allow_html=True)
else:
    st.markdown('<h1 style="color:#1976d2; margin:0;">👑 Challengevala</h1>', unsafe_allow_html=True)

st.markdown('<h1 class="major-title">📈 Elite Quant Dashboard & Auto-Evolving AI</h1>', unsafe_allow_html=True)
st.markdown("---")

# --- API & Categorization ---
model = None
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash")

def categorize_asset(name):
    name = str(name).upper()
    if name.startswith('C-') or name.startswith('P-'):
        return 'BTC/ETH Options' if 'BTC' in name or 'ETH' in name else 'Crypto Options'
    if ' CE' in name or ' PE' in name: return 'NSE Options'
    return 'Futures/Spot'

# --- File Uploader ---
uploaded_files = st.file_uploader("📥 Drag & Drop CSVs", accept_multiple_files=True, type=['csv'])

if uploaded_files:
    all_data = []
    for f in uploaded_files:
        df = pd.read_csv(f)
        if 'Realised P&L' in df.columns: # Delta
            df['P&L'] = pd.to_numeric(df['Realised P&L'], errors='coerce').fillna(0) * 85
            df['Date'] = pd.to_datetime(df['Time'].str[:10]).dt.date
            df['Time_Exact'] = pd.to_datetime(df['Time'].str[:19])
            df['Name'] = df['Contract']
            all_data.append(df[['Date', 'Time_Exact', 'Name', 'P&L']])
        elif 'Date' in df.columns: # Dhan
            df = df[df['Buy/Sell'].isin(['BUY', 'SELL'])].copy()
            df['P&L'] = df.apply(lambda r: r['Trade Value'] if r['Buy/Sell'] == 'SELL' else -r['Trade Value'], axis=1)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            df['Time_Exact'] = pd.to_datetime(df['Time'], format='mixed')
            all_data.append(df[['Date', 'Time_Exact', 'Name', 'P&L']])

    if all_data:
        final_df = pd.concat(all_data)
        final_df['Category'] = final_df['Name'].apply(categorize_asset)
        
        # --- Metrics ---
        st.markdown("<h4 style='color: #444;'>📊 Performance Matrix</h4>", unsafe_allow_html=True)
        pnl = final_df['P&L'].sum()
        wins = len(final_df[final_df['P&L'] > 0])
        losses = len(final_df[final_df['P&L'] < 0])
        total = wins + losses
        wr = (wins / total * 100) if total > 0 else 0

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Net P&L", f"₹{pnl:,.0f}")
        m2.metric("Win Rate", f"{wr:.1f}%")
        m3.metric("Total Trades", total)
        m4.metric("Wins", wins)
        m5.metric("Losses", losses)

        # --- Charts ---
        st.markdown("---")
        daily = final_df.groupby('Date')['P&L'].sum().reset_index()
        daily['Equity'] = daily['P&L'].cumsum()
        
        fig1 = px.area(daily, x='Date', y='Equity', title="Portfolio Growth")
        fig1.update_traces(line_color="#1976d2", fillcolor="rgba(25, 118, 210, 0.05)")
        fig1.update_layout(margin=dict(l=10, r=10, t=40, b=10), plot_bgcolor="white")
        st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})

        c1, c2 = st.columns(2)
        with c1:
            cat_df = final_df.groupby('Category')['P&L'].sum().reset_index()
            fig2 = px.bar(cat_df, x='Category', y='P&L', title="P&L by Category", 
                          color=cat_df['P&L'] > 0, color_discrete_map={True: "#00CC96", False: "#EF553B"})
            fig2.update_layout(margin=dict(l=10, r=10, t=40, b=10), showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)
        with c2:
            final_df['Hour'] = final_df['Time_Exact'].dt.hour
            hr_df = final_df.groupby('Hour')['P&L'].sum().reset_index()
            fig3 = px.bar(hr_df, x='Hour', y='P&L', title="P&L by Hour",
                          color=hr_df['P&L'] > 0, color_discrete_map={True: "#00CC96", False: "#EF553B"})
            fig3.update_layout(margin=dict(l=10, r=10, t=40, b=10), showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)

        # --- AI & Timeline ---
        st.markdown("---")
        if st.button("Generate AI Horizon Study"):
            stats = final_df.groupby(final_df['Time_Exact'].dt.hour).agg(Net=('P&L','sum'), Count=('P&L','count'), Wins=('P&L', lambda x: (x>0).sum())).reset_index()
            stats['WR'] = (stats['Wins']/stats['Count']*100).round(1)
            
            st.markdown(f'<div class="timeline-box"><b>💡 AI Study:</b> Focus on your most profitable hours.</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="timeline-box"><b>📊 Win Rate Timeline</b>', unsafe_allow_html=True)
            for _, r in stats.iterrows():
                color = "#00CC96" if r['WR'] >= 60 else ("#EF553B" if r['WR'] <= 40 else "#1976d2")
                st.markdown(f"""<div class='trade-row'><div class='trade-time'>{int(r['Time_Exact'])}:00</div><div class='trade-progress-wrapper'><div class='trade-progress-bar' style='width: {r['WR']}%; background-color: {color}; color: white; font-size: 12px; font-weight: bold;'>&nbsp;{r['WR']}%</div></div><div class='trade-pnl' style='color: {"#00CC96" if r["Net"]>=0 else "#EF553B"}'>₹{r['Net']:,.0f}</div></div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
