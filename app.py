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

# --- API Setup (Auto-Detect Model) ---
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

    # --- Raw Data (Hidden by Default) ---
    with st.expander("📝 Raw Trade Data (No editing needed)"):
        st.dataframe(df, use_container_width=True)

    # --- DEEP AI ANALYSIS ---
    st.markdown("---")
    st.subheader("🤖 Gemini Deep Observer")
    st.write("Gemini aapke trades ko analyze karke losses ke patterns dhoondhega.")
    
    if st.button("Start Deep Analysis"):
        if model is not None:
            with st.spinner("Gemini aapka data observe kar raha hai..."):
                try:
                    # Sirf relevant data AI ko dena (Time, Price, P&L, Side)
                    analysis_df = df[['Date_Clean', 'P&L_Clean']].copy()
                    if 'Time' in df.columns: analysis_df['Full_Time'] = df['Time']
                    if 'Contract' in df.columns: analysis_df['Asset'] = df['Contract']
                    if 'Name' in df.columns: analysis_df['Asset'] = df['Name']
                    
                    data_string = analysis_df.tail(40).to_string()
                    
                    prompt = f"""
                    You are a professional trading data scientist and coach. 
                    Analyze this raw trading data for patterns. 
                    
                    Your Task:
                    1. Look for recurring losses: Specific times of the day, specific assets, or frequency.
                    2. Identify where the trader is doing well.
                    3. Suggest 2-3 specific technical improvements to reduce losses.
                    
                    Language Requirement: 
                    Respond in 'Hinglish' (mixture of Hindi and English) like a friendly mentor.
                    Keep the tone direct and insightful.
                    
                    Trade Data:
                    {data_string}
                    """
                    
                    response = model.generate_content(prompt)
                    st.info(response.text)
                except Exception as e:
                    st.error(f"AI Error: {e}")
        else:
            st.error("⚠️ AI connected nahi hai.")
else:
    st.info("👆 Please upload your CSV files to start observation.")
