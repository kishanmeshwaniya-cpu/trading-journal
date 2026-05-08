import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai

# --- Page Setup ---
st.set_page_config(page_title="AI Trading Observer", page_icon="🤖", layout="wide")

st.markdown("""
    <style>
    .stMetric {background-color: #f0f2f6; padding: 15px; border-radius: 10px;}
    .stExpander {border: 1px solid #e6e9ef; border-radius: 10px;}
    </style>
""", unsafe_allow_html=True)

st.title("🤖 AI Trading Observer (Deep Analysis)")

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

# --- File Uploader ---
uploaded_files = st.file_uploader("📥 Upload Dhan or Delta CSV", accept_multiple_files=True, type=['csv'])

if uploaded_files:
    df_list = [pd.read_csv(f) for f in uploaded_files]
    df = pd.concat(df_list, ignore_index=True)
    
    st.markdown("---")
    
    # Defaults
    df['P&L_Clean'] = 0.0
    df['Date_Clean'] = pd.NaT
    wins, losses, total_pnl = 0, 0, 0.0
    currency = "₹"
    
    # ---------------------------------------------
    # DATA PROCESSING FOR DASHBOARD CHARTS
    # ---------------------------------------------
    # Delta Detection
    if 'Time' in df.columns and 'Realised P&L' in df.columns:
        df['Date_Clean'] = pd.to_datetime(df['Time'].astype(str).str[:10], errors='coerce').dt.date
        df['P&L_Clean'] = pd.to_numeric(df['Realised P&L'], errors='coerce').fillna(0) * 85
        actual_trades = df[df['P&L_Clean'] != 0]
        wins = len(actual_trades[actual_trades['P&L_Clean'] > 0])
        losses = len(actual_trades[actual_trades['P&L_Clean'] < 0])
        total_pnl = df['P&L_Clean'].sum()

    # Dhan Detection
    elif 'Date' in df.columns and 'Trade Value' in df.columns:
        df = df[df['Buy/Sell'].astype(str).str.upper().isin(['BUY', 'SELL'])].copy()
        df['Date_Clean'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        df['Cashflow'] = df.apply(lambda r: r['Trade Value'] if str(r['Buy/Sell']).upper() == 'SELL' else -r['Trade Value'], axis=1)
        df['P&L_Clean'] = df['Cashflow']
        total_pnl = df['Cashflow'].sum()
        grouped = df.groupby(['Date_Clean', 'Name'])['Cashflow'].sum().reset_index()
        wins = len(grouped[grouped['Cashflow'] > 0])
        losses = len(grouped[grouped['Cashflow'] < 0])

    # --- Metrics ---
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    st.subheader("📊 Current Performance")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Net P&L ({currency})", f"{total_pnl:,.2f}")
    c2.metric("Win Rate", f"{win_rate:.1f}%")
    c3.metric("Losing Trades", losses)
    c4.metric("Profitable Trades", wins)

    # --- Charts ---
    if not df['Date_Clean'].isna().all() and total_pnl != 0:
        st.markdown("---")
        daily = df.groupby('Date_Clean')['P&L_Clean'].sum().reset_index()
        daily['Equity Curve'] = daily['P&L_Clean'].cumsum()
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(px.area(daily, x='Date_Clean', y='Equity Curve', title="📈 Portfolio Value"), use_container_width=True)
        with col_b:
            fig = px.bar(daily, x='Date_Clean', y='P&L_Clean', title="📅 Daily Profit/Loss", color=daily['P&L_Clean'] > 0, color_discrete_map={True: "#00CC96", False: "#EF553B"})
            st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------
    # DEEP AI ANALYSIS (RAW LEDGER FEED)
    # ---------------------------------------------
    st.markdown("---")
    st.subheader("🕵️‍♂️ Deep Quant Analysis")
    st.write("Gemini aapke exact entry/exit timings aur asset patterns ko observe karega.")
    
    if st.button("Analyze Trade Footprints"):
        if model is not None:
            with st.spinner("Scanning time, assets, and consecutive trade patterns..."):
                try:
                    # AI ko raw chronological data dena (Taki wo time aur revenge trading pakad sake)
                    ai_cols = []
                    for col in ['Date', 'Time', 'Name', 'Contract', 'Buy/Sell', 'Side', 'Trade Value', 'Realised P&L']:
                        if col in df.columns: ai_cols.append(col)
                    
                    ai_data = df[ai_cols].tail(50).to_string(index=False)
                    
                    prompt = f"""
                    Tu ek elite, brutal, aur highly specific Data Analyst/Trading Coach hai.
                    Tera kaam hai is RAW chronological trading ledger se HIDDEN PATTERNS nikalna.
                    Generic gyan (like "use stoploss") BILKUL NAHI Dena hai. Mujhe strictly data-driven observation chahiye.
                    
                    CRITICAL RULES FOR READING DATA:
                    1. If you see 'Buy/Sell' and 'Trade Value' (Dhan Broker): A BUY and SELL of the same 'Name' on the same 'Date' is ONE complete trade. The difference is the actual Profit/Loss. DO NOT treat the raw 'Trade Value' as profit.
                    2. Observe the 'Time' carefully: Are losses happening at a specific hour? Are trades placed within minutes of each other (revenge trading)? Which specific asset ('Name'/'Contract') causes the most bleed?
                    
                    Respond in crisp Hinglish (bullet points only, no essays). Structure it exactly like this:
                    
                    🔍 **Deep Data Patterns Observed:**
                    * (Dynamically list specific findings. e.g., "Tune NIFTY 24450 CE pe 12:31 se 12:33 ke beech back-to-back overtrading ki hai.")
                    * (Point out time-based patterns or specific asset struggles based on the data provided.)
                    * (Add as many solid patterns as you find, don't limit to just 2.)
                    
                    🛠️ **Precision Fixes:**
                    * (How to fix these EXACT specific patterns. E.g., "11 AM ke baad continuous NIFTY trades avoid kar.")
                    
                    Here is the chronological ledger:
                    {ai_data}
                    """
                    
                    response = model.generate_content(prompt)
                    st.info(response.text)
                except Exception as e:
                    st.error(f"AI Error: {e}")
        else:
            st.error("⚠️ AI connected nahi hai.")
else:
    st.info("👆 Please upload your CSV files to start observation.")
