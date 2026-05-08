import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai

# --- Page Setup ---
st.set_page_config(page_title="Smart Trading Journal", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .stMetric {background-color: #f0f2f6; padding: 15px; border-radius: 10px;}
    .stExpander {border: 1px solid #e6e9ef; border-radius: 10px;}
    </style>
""", unsafe_allow_html=True)

st.title("📈 Smart Trading Journal & AI Coach")

# --- API Setup (Gemini Integration) ---
model = None
try:
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Naya Model Name Yahan Update Kiya Hai 👇
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        st.sidebar.warning("⚠️ API Key Missing! Manage App > Settings > Secrets mein check karein.")
except Exception as e:
    pass

# --- File Uploader ---
uploaded_files = st.file_uploader("📥 Upload Dhan or Delta CSV", accept_multiple_files=True, type=['csv'])

if uploaded_files:
    df_list = [pd.read_csv(f) for f in uploaded_files]
    df = pd.concat(df_list, ignore_index=True)
    
    st.markdown("---")
    
    df['P&L_Clean'] = 0.0
    df['Date_Clean'] = pd.NaT
    wins, losses, total_pnl = 0, 0, 0.0
    currency = "₹"

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

    # --- Metrics Bar ---
    win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
    st.subheader("📊 Performance Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"Total P&L ({currency})", f"{total_pnl:,.2f}")
    c2.metric("Win Rate", f"{win_rate:.1f}%")
    c3.metric("Profitable Trades", wins)
    c4.metric("Losing Trades", losses)

    # --- Charts ---
    if not df['Date_Clean'].isna().all() and total_pnl != 0:
        st.markdown("---")
        daily = df.groupby('Date_Clean')['P&L_Clean'].sum().reset_index()
        daily['Equity Curve'] = daily['P&L_Clean'].cumsum()
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.plotly_chart(px.area(daily, x='Date_Clean', y='Equity Curve', title="📈 Equity Growth"), use_container_width=True)
        with col_b:
            fig = px.bar(daily, x='Date_Clean', y='P&L_Clean', title="📅 Daily P&L", color=daily['P&L_Clean'] > 0, color_discrete_map={True: "#00CC96", False: "#EF553B"})
            st.plotly_chart(fig, use_container_width=True)

    # --- THE DROPDOWN (Trade Log) ---
    st.markdown("---")
    with st.expander("📖 Click to view/edit Detailed Trade Log (Setup & Emotions)"):
        st.write("Apne trades ke liye Setup aur Emotion columns bharein:")
        if 'Setup' not in df.columns: df.insert(0, 'Setup', "")
        if 'Emotion' not in df.columns: df.insert(1, 'Emotion', "")
        edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)

    # --- AI COACH ---
    st.markdown("---")
    st.subheader("🤖 Gemini AI Trading Report")
    if st.button("Analyze My Trading Psychology"):
        if model is not None:
            with st.spinner("Gemini is reading your trades..."):
                try:
                    ai_data = edited_df[['Setup', 'Emotion', 'P&L_Clean']].tail(20).to_string()
                    prompt = f"""Analyze these recent trades. 
                    Focus on: 
                    1. Consistency of the Setups.
                    2. Any psychological patterns in the 'Emotion' column.
                    3. Give 1 specific rule to follow for tomorrow based on this data.
                    Keep it short and professional.
                    Data: {ai_data}"""
                    
                    response = model.generate_content(prompt)
                    st.info(response.text)
                except Exception as e:
                    st.error(f"AI Error: {e}")
        else:
            st.error("⚠️ AI connection fail ho gaya. Kripya dhyan se Secrets mein GEMINI_API_KEY check karein. Pura format ekdum correct hona chahiye.")
else:
    st.info("👆 Please upload your CSV files to see the magic!")
