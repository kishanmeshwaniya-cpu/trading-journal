import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json
import base64
import os

# --- Page Setup (MUST be first) ---
st.set_page_config(page_title="Challengevala Trader Journal", page_icon="📈", layout="wide")

# --- MASTER STRICT CSS (Removing Scrollbars & Enhancing Shadows) ---
st.markdown("""
    <style>
    /* 1. Page Background & Clean Look */
    .stApp { background-color: #fcfcfc; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; }

    /* 2. Heading Branding matching Brand Blue */
    .major-title {
        text-align: left; 
        color: #1976d2; /* Brand Blue */
        margin-top: 15px; 
        margin-bottom: 5px; 
        font-size: 38px; 
        font-weight: 800;
        line-height: 1.2;
    }

    /* 3. PREMIUM METRICS LAYOUT with Improved Shadow Depth */
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"] { padding: 0 10px; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px !important;
        border-radius: 20px !important;
        border: 1px solid #eeeeee !important;
        /* Improved Shadow: Multi-layered for soft depth feel */
        box-shadow: 0 10px 25px rgba(0,0,0,0.05), 0 4px 10px rgba(0,0,0,0.02) !important;
        width: 100% !important;
        display: flex;
        flex-direction: column;
        justify-content: center;
        min-height: 120px;
    }
    div[data-testid="stMetric"] label { color: #555; font-weight: bold; font-size: 14px; margin-bottom: 5px; }
    div[data-testid="stMetricValue"] > div { color: #1976d2; font-size: 28px !important; font-weight: 700 !important; }

    /* 4. FIXING VERTICAL SCROLLBARS ON CHARTS */
    /* Targeting the plotly container to remove overflow */
    div[data-testid="stPlotlyChart"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 20px;
        border: 1px solid #eeeeee;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05) !important;
        margin-bottom: 20px;
        overflow: hidden !important; /* Forces scrollbars to disappear */
    }
    iframe { overflow: hidden !important; border: none !important; }

    /* 5. Minimalist File Uploader Highlighted with Brand Blue */
    div[data-testid="stFileUploader"] {
        background-color: white;
        border-radius: 15px;
        padding: 10px;
        border: 2px solid #1976d2; /* Highlight with Brand Color */
        margin-bottom: 20px;
    }

    /* 6. TIMELINE & AI BOXES with Depth */
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
    .timeline-title {color: #1976d2; font-weight: bold; font-size: 18px; margin-bottom: 15px;}
    
    /* Progress Bar Styling */
    .trade-row { display: flex; align-items: center; margin-bottom: 12px; min-height: 40px; width: 100%; }
    .trade-time { width: 10%; min-width: 70px; font-weight: bold; font-size: 15px; color: #444; }
    .trade-progress-wrapper { width: 70%; background-color: #f0f2f6; border-radius: 8px; height: 28px; position: relative; overflow: hidden; margin: 0 15px; }
    .trade-progress-bar { height: 100%; border-radius: 8px; display: flex; align-items: center; padding-left: 10px; }
    .trade-win-text { font-size: 13px; font-weight: bold; white-space: nowrap; }
    .trade-pnl { width: 20%; min-width: 130px; text-align: right; font-weight: bold; font-size: 17px; }
    
    /* 7. Plotly hide modebar */
    .modebar { display: none !important; }
    
    /* Highlighting buttons with Brand Color */
    .stButton>button {
        background-color: #1976d2 !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        padding: 10px 25px !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- HEADER (LOGO THEN HEADING BELOW) ---
logo_path = "logo-full.png"
if os.path.exists(logo_path):
    with open(logo_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
        st.markdown(f'<img src="data:image/png;base64,{encoded_string}" style="max-width: 250px; margin-bottom: 10px;">', unsafe_allow_html=True)
else:
    st.markdown('<h1 style="color:#1976d2; margin:0;">👑 CT</h1>', unsafe_allow_html=True)

st.markdown('<h1 class="major-title">📈 Elite Quant Dashboard & Auto-Evolving AI</h1>', unsafe_allow_html=True)
st.markdown("---")

# --- API Setup ---
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        model_name = next((m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods), "gemini-1.5-flash")
        model = genai.GenerativeModel(model_name)
    else:
        st.sidebar.warning("⚠️ API Key Missing!")
except Exception as e:
    pass

# --- Categorization Logic ---
def categorize_asset(name):
    name = str(name).upper()
    if name.startswith('C-') or name.startswith('P-'):
        if 'BTC' in name: return 'BTC Options'
        if 'ETH' in name: return 'ETH Options'
        return 'Crypto Options'
    if ' CE' in name or ' PE' in name or name.endswith('CE') or name.endswith('PE'):
        if 'BANK' in name: return 'BankNifty Options'
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
    for f in uploaded_files:
        temp_df = pd.read_csv(f)
        if 'Time' in temp_df.columns and 'Realised P&L' in temp_df.columns:
            temp_df['P&L_Clean'] = pd.to_numeric(temp_df['Realised P&L'], errors='coerce').fillna(0) * 85
            temp_df = temp_df[temp_df['P&L_Clean'] != 0].copy()
            temp_df['Date_Clean'] = pd.to_datetime(temp_df['Time'].astype(str).str[:10], errors='coerce').dt.date
            temp_df['Trade_Time'] = pd.to_datetime(temp_df['Time'].astype(str).str[:19], errors='coerce')
            temp_df['Asset'] = temp_df['Contract']
            all_processed_data.append(temp_df[['Date_Clean', 'Trade_Time', 'Asset', 'P&L_Clean']])
        elif 'Date' in temp_df.columns and 'Trade Value' in temp_df.columns:
            temp_df = temp_df[temp_df['Buy/Sell'].astype(str).str.upper().isin(['BUY', 'SELL'])].copy()
            temp_df['Cashflow'] = temp_df.apply(lambda r: r['Trade Value'] if str(r['Buy/Sell']).upper() == 'SELL' else -r['Trade Value'], axis=1)
            dhan_grouped = temp_df.groupby([pd.to_datetime(temp_df['Date']).dt.date, 'Name']).agg({'Cashflow': 'sum', 'Time': 'max'}).reset_index()
            dhan_grouped.columns = ['Date_Clean', 'Asset', 'P&L_Clean', 'Time']
            dhan_grouped = dhan_grouped[dhan_grouped['P&L_Clean'] != 0].copy()
            dhan_grouped['Trade_Time'] = pd.to_datetime(dhan_grouped['Time'], format='mixed', errors='coerce')
            all_processed_data.append(dhan_grouped[['Date_Clean', 'Trade_Time', 'Asset', 'P&L_Clean']])

    if all_processed_data:
        analytics_df = pd.concat(all_processed_data, ignore_index=True)
        analytics_df['Category'] = analytics_df['Asset'].apply(categorize_asset)
        
        total_pnl = analytics_df['P&L_Clean'].sum()
        wins = len(analytics_df[analytics_df['P&L_Clean'] > 0])
        losses = len(analytics_df[analytics_df['P&L_Clean'] < 0])
        total_trades = wins + losses 
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

        st.markdown("<h4 style='color: #1976d2; margin-bottom: 15px;'>📊 Combined Performance Matrix</h4>", unsafe_allow_html=True)
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Net P&L", f"₹{total_pnl:,.2f}")
        m2.metric("Win Rate", f"{win_rate:.1f}%")
        m3.metric("Total Trades", total_trades)
        m4.metric("Win Trades", wins)
        m5.metric("Loss Trades", losses)

        # --- Visual Data Insights (Scrollbar Fixed) ---
        st.markdown("---")
        st.markdown("<h4 style='color: #1976d2; margin-bottom: 15px;'>👁️ Visual Data Insights</h4>", unsafe_allow_html=True)
        
        daily = analytics_df.groupby('Date_Clean')['P&L_Clean'].sum().reset_index()
        daily['Equity Curve'] = daily['P&L_Clean'].cumsum()
        
        # Plotly chart with smaller margins to ensure it fits without scrolling
        fig_eq = px.area(daily, x='Date_Clean', y='Equity Curve', title="Total Portfolio Growth",
                         labels={'Date_Clean': 'Trading Date', 'Equity Curve': 'Total Equity (₹)'})
        fig_eq.update_traces(line_color="#1976d2", fillcolor="rgba(25, 118, 210, 0.1)")
        fig_eq.update_layout(margin=dict(l=10, r=10, t=40, b=10), hovermode=False, plot_bgcolor="white", paper_bgcolor="white") 
        st.plotly_chart(fig_eq, use_container_width=True, config={'displayModeBar': False})
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            cat_pnl = analytics_df.groupby('Category')['P&L_Clean'].sum().reset_index()
            fig_asset = px.bar(cat_pnl, x='Category', y='P&L_Clean', title="P&L by Category", 
                               labels={'Category': 'Category', 'P&L_Clean': 'Net P&L (₹)'},
                               color=cat_pnl['P&L_Clean'] > 0, color_discrete_map={True: "#00CC96", False: "#EF553B"})
            fig_asset.update_layout(margin=dict(l=10, r=10, t=40, b=10), showlegend=False, hovermode=False, plot_bgcolor="white", paper_bgcolor="white")
            st.plotly_chart(fig_asset, use_container_width=True, config={'displayModeBar': False})
            
        with col_g2:
            if not analytics_df['Trade_Time'].isna().all():
                analytics_df['Hour'] = analytics_df['Trade_Time'].dt.hour
                time_pnl = analytics_df.groupby('Hour')['P&L_Clean'].sum().reset_index()
                time_pnl['Hour_Label'] = time_pnl['Hour'].apply(lambda x: f"{int(x):02d}:00")
                fig_time = px.bar(time_pnl, x='Hour_Label', y='P&L_Clean', title="P&L by Hour", 
                                  labels={'Hour_Label': 'Time', 'P&L_Clean': 'Net P&L (₹)'},
                                  color=time_pnl['P&L_Clean'] > 0, color_discrete_map={True: "#00CC96", False: "#EF553B"})
                fig_time.update_layout(margin=dict(l=10, r=10, t=40, b=10), showlegend=False, hovermode=False, plot_bgcolor="white", paper_bgcolor="white")
                st.plotly_chart(fig_time, use_container_width=True, config={'displayModeBar': False})

        # --- Deep Time-Based AI Study ---
        st.markdown("---")
        st.markdown("<h4 style='color: #1976d2; margin-bottom: 15px;'>⏳ Gemini Core: Time Horizon Study</h4>", unsafe_allow_html=True)
        
        if st.button("Generate Time Horizon Study"):
            if model is not None:
                with st.spinner("Analyzing ultimate time edge..."):
                    try:
                        analytics_df['Hour'] = analytics_df['Trade_Time'].dt.hour
                        time_stats = analytics_df.groupby('Hour').agg(
                            Net_PnL=('P&L_Clean', 'sum'),
                            Total_Trades=('P&L_Clean', 'count'),
                            Wins=('P&L_Clean', lambda x: (x > 0).sum())
                        ).reset_index().sort_values('Hour')
                        
                        time_stats['Win_Rate_%'] = (time_stats['Wins'] / time_stats['Total_Trades'] * 100).round(1)
                        time_stats['Time_Label'] = time_stats['Hour'].apply(lambda x: f"{int(x):02d}:00")
                        ai_feed = time_stats[['Time_Label', 'Net_PnL', 'Win_Rate_%', 'Total_Trades']].to_string(index=False)
                        
                        prompt = f"Act as Quant Analyst. Deeply analyze this Hourly P&L and Win Rate data. Give 3 short bullet points: Golden Zone, Danger Zone, and key advice. Keep it clean and direct. Data: {ai_feed}"
                        response = model.generate_content(prompt)
                        
                        st.markdown(f'''<div class="timeline-box"><p class="timeline-title">💡 Gemini Quant Analysis</p><p style='color: #333; font-size: 15px; white-space: pre-wrap;'>{response.text.strip()}</p></div>''', unsafe_allow_html=True)
                        
                        st.markdown('<div class="timeline-box"><p class="timeline-title">📊 Win Rate & Profit Timeline</p>', unsafe_allow_html=True)
                        for _, row in time_stats.iterrows():
                            pnl_color = "#00CC96" if row['Net_PnL'] >= 0 else "#EF553B"
                            bar_color = "#1976d2"
                            if row['Win_Rate_%'] >= 60: bar_color = "#00CC96"
                            elif row['Win_Rate_%'] <= 40: bar_color = "#EF553B"
                            st.markdown(f"""<div class='trade-row'><div class='trade-time'>{row['Time_Label']}</div><div class='trade-progress-wrapper'><div class='trade-progress-bar' style='width: {row['Win_Rate_%']}%; background-color: {bar_color};'><span class='trade-win-text' style='color: white;'>{row['Win_Rate_%']}%</span></div></div><div class='trade-pnl' style='color: {pnl_color};'>₹{row['Net_PnL']:,.0f}</div></div>""", unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"AI Error: {e}")
