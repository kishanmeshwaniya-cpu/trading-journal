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
    ai_data = pd.DataFrame()

    # Delta Detection
    if 'Time' in df.columns and 'Realised P&L' in df.columns:
        df['Date_Clean'] = pd.to_datetime(df['Time'].astype(str).str[:10], errors='coerce').dt.date
        df['P&L_Clean'] = pd.to_numeric(df['Realised P&L'], errors='coerce').fillna(0) * 85
        actual_trades = df[df['P&L_Clean'] != 0]
        wins = len(actual_trades[actual_trades['P&L_Clean'] > 0])
        losses = len(actual_trades[actual_trades['P&L_Clean'] < 0])
        total_pnl = df['P&L_Clean'].sum()
        
        # Prepare Data for AI
        ai_data = actual_trades[['Date_Clean', 'Contract', 'P&L_Clean']].copy()
        ai_data.rename(columns={'P&L_Clean': 'Net_Profit_Loss', 'Contract': 'Asset'}, inplace=True)

    # Dhan Detection
    elif 'Date' in df.columns and 'Trade Value' in df.columns:
        df = df[df['Buy/Sell'].astype(str).str.upper().isin(['BUY', 'SELL'])].copy()
        df['Date_Clean'] = pd.to_datetime(df['Date'], errors='coerce').dt.date
        df['Cashflow'] = df.apply(lambda r: r['Trade Value'] if str(r['Buy/Sell']).upper() == 'SELL' else -r['Trade Value'], axis=1)
        df['P&L_Clean'] = df['Cashflow']
        total_pnl = df['Cashflow'].sum()
        
        # Group by Day & Asset to get NET PnL (Fixes the Buy/Sell value confusion)
        grouped = df.groupby(['Date_Clean', 'Name'])['Cashflow'].sum().reset_index()
        wins = len(grouped[grouped['Cashflow'] > 0])
        losses = len(grouped[grouped['Cashflow'] < 0])
        
        # Prepare Data for AI
        ai_data = grouped[grouped['Cashflow'] != 0].copy()
        ai_data.rename(columns={'Cashflow': 'Net_Profit_Loss', 'Name': 'Asset'}, inplace=True)

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

    # --- DEEP AI ANALYSIS ---
    st.markdown("---")
    st.subheader("🤖 Gemini Deep Observer")
    st.write("Click below for a crisp, visual summary of your trading patterns.")
    
    if st.button("Generate Crisp Report"):
        if model is not None and not ai_data.empty:
            with st.spinner("Analyzing strictly Net P&L data..."):
                try:
                    data_string = ai_data.tail(30).to_string(index=False)
                    
                    prompt = f"""
                    You are a strict, no-nonsense trading coach. 
                    DO NOT WRITE ESSAYS. DO NOT USE LONG PARAGRAPHS.
                    
                    Here is the trader's NET Profit and Loss per completed trade:
                    {data_string}
                    
                    *Note: Negative numbers in 'Net_Profit_Loss' are true losses. Positive numbers are true profits.*
                    
                    Provide a brief, visual report in Hinglish using EXACTLY this structure:
                    
                    🔴 **Top 2 Mistakes (Patterns):**
                    * (Mistake 1 in 1 brief line)
                    * (Mistake 2 in 1 brief line)
                    
                    💡 **How to Improve:**
                    * (Actionable step 1 in 1 brief line)
                    * (Actionable step 2 in 1 brief line)
                    
                    📈 **Expected Result (If Improved):**
                    * (What will change in their P&L or Win Rate - 1 line)
                    """
                    
                    response = model.generate_content(prompt)
                    st.success(response.text)
                except Exception as e:
                    st.error(f"AI Error: {e}")
        else:
            st.error("⚠️ Data insufficient ya AI connect nahi hua.")
else:
    st.info("👆 Please upload your CSV files to start observation.")
