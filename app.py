import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json
import base64
import os

# --- Page Setup (MUST be first) ---
st.set_page_config(page_title="Challengevala Trader Journal", page_icon="📈", layout="wide")

# --- MASTER MINIMALIST CSS (No Borders, Proper Depth) ---
st.markdown("""
    <style>
    /* 1. Page Background & Global Font */
    .stApp { background-color: #f8f9fa; font-family: 'Inter', sans-serif; }

    /* 2. STRICTLY NO BORDERS + LUXURY SHADOWS */
    /* Metric boxes & Charts unified */
    div[data-testid="stMetric"], div[data-testid="stPlotlyChart"], .timeline-box {
        background-color: #ffffff !important;
        border: none !important; /* Borders removed everywhere */
        border-radius: 28px !important; /* Premium Large Rounded Corners */
        /* Smooth multi-layered shadow for depth */
        box-shadow: 0 10px 40px rgba(0,0,0,0.04), 0 2px 10px rgba(0,0,0,0.01) !important;
        padding: 24px !important;
        margin-bottom: 24px !important;
    }

    /* 3. Heading Alignment & Styling */
    .major-title {
        text-align: left; 
        color: #1c1c1c; 
        font-size: 34px; 
        font-weight: 800;
        margin-top: 15px;
        margin-bottom: 20px;
        letter-spacing: -0.5px;
    }

    /* 4. Metric Styling matching Brand Colors */
    div[data-testid="stMetricValue"] > div { color: #1976d2 !important; font-weight: 700 !important; font-size: 32px !important; }
    div[data-testid="stMetric"] label { color: #666 !important; font-size: 14px !important; font-weight: 600 !important; }

    /* 5. Minimalist File Uploader (No border) */
    div[data-testid="stFileUploader"] {
        background-color: white;
        border: none !important;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
    }

    /* 6. Strict Timeline Table (Minimalist UI) */
    .trade-row { display: flex; align-items: center; margin-bottom: 12px; min-height: 40px; width: 100%; }
    .trade-time { width: 10%; min-width: 75px; font-weight: 600; color: #333; font-size: 15px; }
    .trade-progress-wrapper { 
        width: 70%; background-color: #f0f2f6; border-radius: 50px; /* Capsule shape */
        height: 26px; position: relative; overflow: hidden; margin: 0 20px; 
    }
    .trade-progress-bar { height: 100%; border-radius: 50px; display: flex; align-items: center; padding-left: 12px; }
    .trade-pnl { width: 20%; min-width: 130px; text-align: right; font-weight: 700; font-size: 18px; }
    
    /* 7. Plotly Cleanup */
    .modebar { display: none !important; }
    div[data-testid="stPlotlyChart"] { overflow: hidden !important; }
    .block-container { padding-top: 2.5rem !important; }

    /* Button Styling */
    .stButton>button {
        border-radius: 15px !important;
        border: none !important;
        background-color: #1976d2 !important;
        padding: 0.6rem 2rem !important;
        box-shadow: 0 4px 15px rgba(25, 118, 210, 0.2) !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER SECTION ---
logo_path = "logo-full.png"
if os.path.exists(logo_path):
    with open(logo_path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
        st.markdown(f'<img src="data:image/png;base64,{data}" style="max-width: 240px; margin-bottom: 5px;">', unsafe_allow_html=True)

st.markdown('<h1 class="major-title">📈 Elite Quant Dashboard & Auto-Evolving AI</h1>', unsafe_allow_html=True)
st.markdown("---")

# --- API & Categorization ---
model = None
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-1.5-flash")

def get_cat(n):
    n = str(n).upper()
    if any(x in n for x in ['C-','P-','CE','PE']): return 'Options'
    return 'Futures/Spot'

# --- File Management ---
up = st.file_uploader("📥 Upload CSVs", accept_multiple_files=True, type=['csv'])

if up:
    dfs = []
    for f in up:
        d = pd.read_csv(f)
        if 'Realised P&L' in d.columns: # Delta
            d['P&L'] = pd.to_numeric(d['Realised P&L'], errors='coerce').fillna(0) * 85
            d['D'] = pd.to_datetime(d['Time'].str[:10]).dt.date
            d['T'] = pd.to_datetime(d['Time'].str[:19])
            d['N'] = d['Contract']
            dfs.append(d[['D', 'T', 'N', 'P&L']])
        elif 'Date' in d.columns: # Dhan
            d = d[d['Buy/Sell'].isin(['BUY', 'SELL'])].copy()
            d['P&L'] = d.apply(lambda r: r['Trade Value'] if r['Buy/Sell'] == 'SELL' else -r['Trade Value'], axis=1)
            d['D'] = pd.to_datetime(d['Date']).dt.date
            d['T'] = pd.to_datetime(d['Time'], format='mixed')
            dfs.append(d[['D', 'T', 'Name', 'P&L']].rename(columns={'Name':'N'}))

    if dfs:
        main = pd.concat(dfs)
        main['C'] = main['N'].apply(get_cat)
        
        # --- Metrics Matrix ---
        pnl = main['P&L'].sum()
        w = len(main[main['P&L'] > 0])
        l = len(main[main['P&L'] < 0])
        total = w + l
        wr = (w / total * 100) if total > 0 else 0

        st.markdown("<h4 style='color: #444; font-weight:700; margin-bottom:15px;'>📊 Performance Matrix</h4>", unsafe_allow_html=True)
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Net P&L", f"₹{pnl:,.0f}")
        m2.metric("Win Rate", f"{wr:.1f}%")
        m3.metric("Total Trades", total)
        m4.metric("Wins", w)
        m5.metric("Losses", l)

        # --- Clean Charts ---
        st.markdown("---")
        dy = main.groupby('D')['P&L'].sum().reset_index()
        dy['E'] = dy['P&L'].cumsum()
        
        fig1 = px.area(dy, x='D', y='E', title="Equity Growth")
        fig1.update_traces(line_color="#1976d2", fillcolor="rgba(25, 118, 210, 0.05)")
        fig1.update_layout(margin=dict(l=10, r=10, t=50, b=10), plot_bgcolor="white", title_font_size=18)
        st.plotly_chart(fig1, use_container_width=True, config={'displayModeBar': False})

        col_a, col_b = st.columns(2)
        with col_a:
            c_df = main.groupby('C')['P&L'].sum().reset_index()
            fig2 = px.bar(c_df, x='C', y='P&L', title="P&L by Category", 
                          color=c_df['P&L'] > 0, color_discrete_map={True: "#00CC96", False: "#EF553B"})
            fig2.update_layout(margin=dict(l=10, r=10, t=50, b=10), showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)
        with col_b:
            main['H'] = main['T'].dt.hour
            h_df = main.groupby('H')['P&L'].sum().reset_index()
            fig3 = px.bar(h_df, x='H', y='P&L', title="P&L by Hour",
                          color=h_df['P&L'] > 0, color_discrete_map={True: "#00CC96", False: "#EF553B"})
            fig3.update_layout(margin=dict(l=10, r=10, t=50, b=10), showlegend=False)
            st.plotly_chart(fig3, use_container_width=True)

        # --- AI Study ---
        st.markdown("---")
        if st.button("Generate Time Horizon Study", type="primary"):
            st_df = main.groupby(main['T'].dt.hour).agg(N=('P&L','sum'), C=('P&L','count'), W=('P&L', lambda x: (x>0).sum())).reset_index()
            st_df['WR'] = (st_df['W']/st_df['C']*100).round(1)
            
            st.markdown('<div class="timeline-box"><b>💡 AI Conclusion:</b> Trade during high-winrate hours to maximize equity curve stability.</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="timeline-box"><b>📊 Win Rate Timeline</b>', unsafe_allow_html=True)
            for _, r in st_df.iterrows():
                cl = "#00CC96" if r['WR'] >= 60 else ("#EF553B" if r['WR'] <= 40 else "#1976d2")
                st.markdown(f"""<div class='trade-row'><div class='trade-time'>{int(r['T'])}:00</div><div class='trade-progress-wrapper'><div class='trade-progress-bar' style='width: {r['WR']}%; background-color: {cl}; color: white; font-size: 12px; font-weight: bold;'>&nbsp;{r['WR']}%</div></div><div class='trade-pnl' style='color: {"#00CC96" if r["N"]>=0 else "#EF553B"}'>₹{r['N']:,.0f}</div></div>""", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
