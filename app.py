import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai

# --- Page Setup ---
st.set_page_config(page_title="Pro Trading Journal", page_icon="📈", layout="wide")

# --- CSS for Professional Look ---
st.markdown("""
    <style>
    .stMetric {background-color: #f0f2f6; padding: 15px; border-radius: 10px;}
    </style>
""", unsafe_allow_html=True)

st.title("📈 Pro Trading Journal & AI Coach")

# --- API Setup ---
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-pro')
except:
    st.sidebar.warning("🔑 Add GEMINI_API_KEY in Streamlit Secrets for AI Coach.")

# --- File Uploader ---
uploaded_files = st.file_uploader("📥 Drop Dhan or Delta CSV here", accept_multiple_files=True, type=['csv'])

if uploaded_files:
    df_list = [pd.read_csv(f) for f in uploaded_files]
    df = pd.concat(df_list, ignore_index=True)
    
    # --- SMART DATA PARSER (Finds Date & PNL columns automatically) ---
    date_col = next((c for c in df.columns if 'time' in c.lower() or 'date' in c.lower()), None)
    pnl_col = next((c for c in df.columns if 'pnl' in c.lower() or 'profit' in c.lower() or 'realized' in c.lower()), None)
    
    # Default values if parsing fails
    total_trades = len(df)
    total_pnl = 0
    win_rate = 0
    
    if pnl_col:
        df['P&L_Clean'] = pd.to_numeric(df[pnl_col], errors='coerce').fillna(0)
        total_pnl = df['P&L_Clean'].sum()
        wins = len(df[df['P&L_Clean'] > 0])
        losses = len(df[df['P&L_Clean'] < 0])
        total_completed = wins + losses
        win_rate = (wins / total_completed * 100) if total_completed > 0 else 0

    st.markdown("---")
    
    # --- 1. KPI METRICS ROW ---
    st.subheader("📊 Key Performance Indicators")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total P&L", f"{total_pnl:.2f}")
    col2.metric("Win Rate", f"{win_rate:.1f}%")
    col3.metric("Total Executions", total_trades)
    col4.metric("Profitable Trades", wins if pnl_col else 0)

    # --- 2. CHARTS SECTION (Tradervue Style) ---
    if date_col and pnl_col:
        st.markdown("---")
        df['Date_Clean'] = pd.to_datetime(df[date_col], errors='coerce').dt.date
        daily_pnl = df.groupby('Date_Clean')['P&L_Clean'].sum().reset_index()
        daily_pnl['Cumulative P&L'] = daily_pnl['P&L_Clean'].cumsum()
        
        # Color coding for Daily P&L
        daily_pnl['Color'] = daily_pnl['P&L_Clean'].apply(lambda x: 'Profit' if x > 0 else 'Loss')
        color_map = {'Profit': '#00CC96', 'Loss': '#EF553B'}

        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            fig1 = px.area(daily_pnl, x='Date_Clean', y='Cumulative P&L', title="📈 Equity Curve (Cumulative P&L)")
            fig1.update_layout(margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig1, use_container_width=True)
            
        with chart_col2:
            fig2 = px.bar(daily_pnl, x='Date_Clean', y='P&L_Clean', title="📅 Daily Net P&L", color='Color', color_discrete_map=color_map)
            fig2.update_layout(margin=dict(l=0, r=0, t=40, b=0), showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

    # --- 3. JOURNAL & TAGS SECTION ---
    st.markdown("---")
    st.subheader("📝 Trade Log & Tags")
    
    if 'Setup' not in df.columns:
        df.insert(0, 'Setup', "")
    if 'Emotion' not in df.columns:
        df.insert(1, 'Emotion', "")
        
    edited_df = st.data_editor(df, num_rows="dynamic", use_container_width=True)
    
    # --- 4. AI COACH SECTION ---
    st.markdown("---")
    st.subheader("🤖 AI Trading Coach")
    if st.button("Generate Performance Analysis"):
        with st.spinner("Analyzing your setups, emotions, and P&L..."):
            try:
                summary_data = edited_df[['Setup', 'Emotion']].copy()
                if pnl_col:
                    summary_data['P&L'] = edited_df[pnl_col]
                    
                prompt = f"""
                You are a strict, professional trading coach analyzing this data.
                Data contains user's setups, emotions, and P&L.
                
                Provide:
                1. What is working (Strengths).
                2. Psychological Traps/Mistakes observed.
                3. Actionable Rule for the next session.
                
                Data: {summary_data.to_string()}
                """
                response = model.generate_content(prompt)
                st.info(response.text)
            except Exception as e:
                st.error("Error generating AI report. Check your Gemini API Key.")
else:
    st.info("👆 Please upload your Dhan or Delta
