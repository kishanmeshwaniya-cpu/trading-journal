import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json

# --- Page Setup (MUST be first) ---
st.set_page_config(page_title="Challengevala Trader Journal", page_icon="📈", layout="wide")

# --- MASTER STRICT & MINIMALIST CSS ---
st.markdown("""
    <style>
    /* 1. Page Background & Default Font */
    .stApp { background-color: #fcfcfc; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }

    /* 2. Global Metric Box Style */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px !important;
        border-radius: 20px !important;
        border: 1px solid #eeeeee !important;
        box-shadow: 0 2px 12px rgba(0,0,0,0.03) !important;
        min-height: 120px;
    }
    div[data-testid="stMetric"] label { color: #666; font-weight: bold; font-size: 14px; margin-bottom: 5px; }
    div[data-testid="stMetricValue"] > div { color: #000; font-size: 28px !important; font-weight: 700 !important; }

    /* 3. Global Plotly Charts Box Style */
    div[data-testid="stPlotlyChart"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 20px;
        border: 1px solid #eeeeee;
        box-shadow: 0 2px 12px rgba(0,0,0,0.03);
    }

    /* 4. Minimalist File Uploader */
    div[data-testid="stFileUploader"] {
        background-color: white;
        border-radius: 15px;
        padding: 10px;
        border: 1px solid #eee;
        margin-bottom: 20px;
    }
    
    /* 5. Plotly hide modebar */
    .modebar { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# --- BRANDING HEADER (Left Logo + Giant Title) ---
col1, col2 = st.columns([1.5, 8.5], gap="medium") # 15% space for logo, 85% for title

with col1:
    try:
        # Aapka logo proper size mein aayega
        st.image("logo-full.png", use_container_width=True)
    except Exception as e:
        st.markdown("<h1 style='color:#1976d2; margin-top: 10px;'>👑 CT</h1>", unsafe_allow_html=True)

with col2:
    # Text removed, Heading made GIANT
    st.markdown("<h1 style='color: #262730; margin-top: 10px; font-size: 42px; font-weight: 900; line-height: 1.2;'>📈 Elite Quant Dashboard & Auto-Evolving AI</h1>", unsafe_allow_html=True)

st.markdown("---")

# --- API Setup ---
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model_name = next((m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods), "gemini-1.5-flash")
        model = genai.GenerativeModel(model_name)
    else:
        st.sidebar.warning("⚠️ API Key Missing! Settings > Secrets mein daalein.")
except Exception as e:
    pass

# --- Helper Function: Smart Categorization ---
def categorize_asset(name):
    name = str(name).upper()
    if name.startswith('C-') or name.startswith('P-'):
        if 'BTC' in name: return 'BTC Options'
        if 'ETH' in name: return 'ETH Options'
        return 'Crypto Options'
    if ' CE' in name or ' PE' in name or name.endswith('CE') or name.endswith('PE'):
        if 'BANKNIFTY' in name or 'BANK' in name: return 'BankNifty Options'
        if 'NIFTY' in name: return 'Nifty Options'
        return 'NSE Options'
    if 'BTC' in name: return 'BTC Futures'
    if 'ETH' in name: return 'ETH Futures'
    if 'NIFTY' in name: return 'Nifty 50 Futures'
    return 'Other'

# --- File Uploader ---
uploaded_files = st.file_uploader("📥 Upload Dhan & Delta CSVs together", accept_multiple_files=True, type=['csv'])

if uploaded_files:
    all_processed_data = []
    
    # --- DUAL ENGINE ---
    for f in uploaded_files:
        temp_df = pd.read_csv(f)
        
        # DELTA
        if 'Time' in temp_df.columns and 'Realised P&L' in temp_df.columns:
            temp_df['P&L_Clean'] = pd.to_numeric(temp_df['Realised P&L'], errors='coerce').fillna(0) * 85
            temp_df = temp_df[temp_df['P&L_Clean'] != 0].copy()
            temp_df['Date_Clean'] = pd.to_datetime(temp_df['Time'].astype(str).str[:10], errors='coerce').dt.date
            temp_df['Trade_Time'] = pd.to_datetime(temp_df['Time'].astype(str).str[:19], errors='coerce')
            temp_df['Asset'] = temp_df['Contract']
            all_processed_data.append(temp_df[['Date_Clean', 'Trade_Time', 'Asset', 'P&L_Clean']])
            
        # DHAN
        elif 'Date' in temp_df.columns and 'Trade Value' in temp_df.columns:
            temp_df = temp_df[temp_df['Buy/Sell'].astype(str).str.upper().isin(['BUY', 'SELL'])].copy()
            temp_df['Cashflow'] = temp_df.apply(lambda r: r['Trade Value'] if str(r['Buy/Sell']).upper() == 'SELL' else -r['Trade Value'], axis=1)
            dhan_grouped = temp_df.groupby([pd.to_datetime(temp_df['Date']).dt.date, 'Name']).agg({'Cashflow': 'sum', 'Time': 'max'}).reset_index()
            dhan_grouped.columns = ['Date_Clean', 'Asset', 'P&L_Clean', 'Time']
            dhan_grouped = dhan_grouped[dhan_grouped['P&L_Clean'] != 0].copy()
            dhan_grouped['Trade_Time'] = pd.to_datetime(dhan_grouped['Time'], format='mixed', errors='coerce')
            all_processed_data.append(dhan_grouped[['Date_Clean', 'Trade_Time', 'Asset', 'P&L_Clean']])

    # Master Data
    if all_processed_data:
        analytics_df = pd.concat(all_processed_data, ignore_index=True)
        analytics_df['Category'] = analytics_df['Asset'].apply(categorize_asset)
        
        total_pnl = analytics_df['P&L_Clean'].sum()
        wins = len(analytics_df[analytics_df['P&L_Clean'] > 0])
        losses = len(analytics_df[analytics_df['P&L_Clean'] < 0])
        
        total_trades = wins + losses 
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        st.markdown("<h4 style='color: #444; margin-bottom: 15px;'>📊 Combined Performance Matrix</h4>", unsafe_allow_html=True)
        
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Net P&L", f"₹{total_pnl:,.2f}")
        m2.metric("Win Rate", f"{win_rate:.1f}%")
        m3.metric("Total Trades", total_trades)
        m4.metric("Win Trades", wins)
        m5.metric("Loss Trades", losses)

        # ---------------------------------------------
        # GRAPHICS ENGINE (Auto-boxed by CSS)
        # ---------------------------------------------
        st.markdown("---")
        st.markdown("<h4 style='color: #444; margin-bottom: 15px;'>👁️ Visual Data Insights</h4>", unsafe_allow_html=True)
        
        daily = analytics_df.groupby('Date_Clean')['P&L_Clean'].sum().reset_index()
        daily['Equity Curve'] = daily['P&L_Clean'].cumsum()
        
        fig_eq = px.area(daily, x='Date_Clean', y='Equity Curve', title="Total Portfolio Growth",
                         labels={'Date_Clean': 'Trading Date', 'Equity Curve': 'Total Equity (₹)'})
        fig_eq.update_traces(line_color="#262730", fillcolor="rgba(38, 39, 48, 0.1)")
        fig_eq.update_layout(hovermode=False, plot_bgcolor="white", paper_bgcolor="white",
                             yaxis=dict(showgrid=True, gridcolor='#f0f2f6')) 
        st.plotly_chart(fig_eq, use_container_width=True, config={'displayModeBar': False})
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            category_pnl = analytics_df.groupby('Category')['P&L_Clean'].sum().reset_index()
            fig_asset = px.bar(category_pnl, x='Category', y='P&L_Clean', title="P&L by Category", 
                               labels={'Category': 'Instrument Category', 'P&L_Clean': 'Net P&L (₹)'},
                               color=category_pnl['P&L_Clean'] > 0, 
                               color_discrete_map={True: "#00CC96", False: "#EF553B"})
            fig_asset.update_layout(showlegend=False, hovermode=False, plot_bgcolor="white", paper_bgcolor="white", xaxis_tickangle=0)
            st.plotly_chart(fig_asset, use_container_width=True, config={'displayModeBar': False})
            
        with col_g2:
            if not analytics_df['Trade_Time'].isna().all():
                analytics_df['Hour'] = analytics_df['Trade_Time'].dt.hour
                time_pnl = analytics_df.groupby('Hour')['P&L_Clean'].sum().reset_index()
                time_pnl['Hour_Label'] = time_pnl['Hour'].apply(lambda x: f"{int(x):02d}:00")
                fig_time = px.bar(time_pnl, x='Hour_Label', y='P&L_Clean', title="P&L by Hour", 
                                  labels={'Hour_Label': 'Time of Day', 'P&L_Clean': 'Net P&L (₹)'},
                                  color=time_pnl['P&L_Clean'] > 0, 
                                  color_discrete_map={True: "#00CC96", False: "#EF553B"})
                fig_time.update_layout(showlegend=False, hovermode=False, plot_bgcolor="white", paper_bgcolor="white")
                st.plotly_chart(fig_time, use_container_width=True, config={'displayModeBar': False})

        # ---------------------------------------------
        # DEEP TIME-BASED AI ENGINE (HTML BUG FIXED)
        # ---------------------------------------------
        st.markdown("---")
        st.markdown("<h4 style='color: #444; margin-bottom: 15px;'>⏳ Gemini Core: Time Horizon Study</h4>", unsafe_allow_html=True)
        
        if st.button("Generate Time Horizon Study"):
            if model is not None:
                with st.spinner("Analyzing data to find ultimate time edge..."):
                    try:
                        analytics_df['Hour'] = analytics_df['Trade_Time'].dt.hour
                        
                        time_stats = analytics_df.groupby('Hour').agg(
                            Net_PnL=('P&L_Clean', 'sum'),
                            Total_Trades=('P&L_Clean', 'count'),
                            Wins=('P&L_Clean', lambda x: (x > 0).sum())
                        ).reset_index()
                        
                        time
